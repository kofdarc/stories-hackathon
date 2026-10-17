"""Deterministic decision arithmetic. No LLM, credentials or network access here.

Every projection reweights historical weekday means to a planning calendar.
Behavioral responses are user assumptions, never inferred causal effects.
"""
from itertools import permutations
from datetime import datetime
from pathlib import Path
import math
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from src.analytics import load_data, baskets

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = dict(module="hours", branch="Garden", weekdays=list(range(7)), days=28,
                start_date="2026-07-01", lookback=56, start_hour=7, end_hour=24,
                hourly_saving=0.0, recapture=0.0, adoption=0.03,
                combo_discount=0.0, extra_cost=0.0, price_change=0.05,
                elasticity=-0.8, basket_exit=0.0, product="All products",
                anchor="Any product", attached="Any product")


def number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return float(value)


def closure(gp, removed_hours, hourly_saving, recapture):
    saved = removed_hours * hourly_saving
    lost = gp * (1 - recapture)
    return dict(net=saved-lost, savings=saved, lost_gp=lost,
                break_even_hourly_cost=lost/removed_hours if removed_hours else None,
                break_even_recapture=max(0.0,1-saved/gp) if gp > 0 else None)


def attachment(eligible, existing, adoption, price_a, price_b, gp_b, discount, extra_cost):
    rebate = discount * (price_a + price_b)
    per_addition = gp_b - rebate - extra_cost
    extra = eligible * adoption
    leakage = existing * rebate
    return dict(net=extra*per_addition-leakage, added_units=extra,
                incremental_unit_gp=per_addition, leakage=leakage,
                break_even_adoption=leakage/(eligible*per_addition)
                if eligible*per_addition > 0 else None)


def price_scenario(revenue, cost, other_gp, change, elasticity, basket_exit):
    if change == 0:
        return dict(net=0.0,quantity_change=0.0,modeled_item_gp=revenue-cost,
                    other_basket_gp_lost=0.0,break_even_item_loss=0.0)
    retention = (1+change)**elasticity
    # Entire-basket exit is a separate conditional loss after own-item response.
    new_gp = (revenue*(1+change)-cost)*retention*(1-basket_exit)
    baseline_gp = revenue-cost
    net = new_gp-baseline_gp-other_gp*basket_exit
    margin_new = revenue*(1+change)-cost
    return dict(net=net, quantity_change=retention*(1-basket_exit)-1,
                modeled_item_gp=new_gp, other_basket_gp_lost=other_gp*basket_exit,
                break_even_item_loss=1-baseline_gp/margin_new if margin_new > 0 else None)


class DecisionEngine:
    def __init__(self, source=None, data=None):
        self.x = data.copy() if data is not None else load_data(source or ROOT/'stories_transactions.csv')
        self.b = baskets(self.x)
        self.products = sorted(self.x['product'].unique().tolist())
        self.branches = sorted(self.x.branch.unique().tolist())
        self.last = self.x.date.max()
        self.first = self.x.date.min()
        self.backtest = self._backtest()

    def metadata(self):
        tomorrow=pd.Timestamp(datetime.now(ZoneInfo('Asia/Beirut')).date())+pd.Timedelta(days=1)
        defaults = dict(DEFAULTS, start_date=str(max(tomorrow,self.last+pd.Timedelta(days=1)).date()),
                        branch=self.branches[0])
        return dict(defaults=defaults, products=self.products, branches=self.branches,
                    source_start=str(self.first.date()), source_end=str(self.last.date()),
                    lines=len(self.x), baskets=len(self.b), revenue=float(self.x.revenue.sum()),
                    gp=float(self.x.gp.sum()), backtest=self.backtest)

    def validate(self, state):
        if not isinstance(state, dict) or set(state)-set(DEFAULTS):
            raise ValueError("Unknown scenario field")
        s = dict(self.metadata()['defaults'], **state)
        if s['module'] not in ('hours', 'combos', 'pricing') or s['branch'] not in self.branches:
            raise ValueError("Choose a valid decision and branch")
        for name, low, high in [('days',7,90),('lookback',28,181),('start_hour',7,23),
                               ('end_hour',8,24),('hourly_saving',0,500),('recapture',0,1),
                               ('adoption',0,1),('combo_discount',0,.5),('extra_cost',0,100),
                               ('price_change',-.3,.5),('elasticity',-5,0),('basket_exit',0,1)]:
            s[name] = number(s[name], low, high, name)
        for name in ('days','lookback','start_hour','end_hour'):
            if not s[name].is_integer():
                raise ValueError(f"{name} must be a whole number")
            s[name] = int(s[name])
        if s['start_hour'] >= s['end_hour']:
            raise ValueError("Opening hour must be before closing hour")
        w = s['weekdays']
        if not isinstance(w,list) or not w or any(type(v) is not int or v not in range(7) for v in w):
            raise ValueError("Select at least one weekday (0=Monday through 6=Sunday)")
        s['weekdays'] = sorted(set(w))
        for name, wildcard in [('product','All products'),('anchor','Any product'),('attached','Any product')]:
            if s[name] != wildcard and s[name] not in self.products:
                raise ValueError(f"Unknown {name}")
        try:
            start = pd.Timestamp(s['start_date'])
            if start.tzinfo or str(start.date()) != s['start_date']:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError("Use a planning date in YYYY-MM-DD format") from None
        if not self.last < start <= self.last+pd.Timedelta(days=730):
            raise ValueError("Planning date must follow the source period and be within two years")
        return s

    def _scope(self, s):
        first = max(self.first, self.last-pd.Timedelta(days=s['lookback']-1))
        historical_dates = pd.date_range(first, self.last)
        hd = pd.Series(historical_dates.dayofweek).value_counts()
        planning = pd.date_range(s['start_date'], periods=s['days'])
        pdays = pd.Series(planning.dayofweek).value_counts()
        weights = {w:float(pdays.get(w,0)/hd.get(w,1)) for w in s['weekdays']}
        x = self.x[self.x.branch.eq(s['branch']) & self.x.date.ge(first)
                   & self.x.weekday.isin(s['weekdays'])].copy()
        x['weight'] = x.weekday.map(weights)
        return x, first, weights, int(sum(pdays.get(w,0) for w in s['weekdays']))

    def run(self, state):
        s = self.validate(state)
        x, first, weights, active_days = self._scope(s)
        b = baskets(x)
        baseline_gp = float((x.gp*x.weight).sum())
        baseline_revenue = float((x.revenue*x.weight).sum())
        bweights = b.weekday.map(weights)
        common = dict(state=s, period=dict(start=s['start_date'], days=s['days'], active_days=active_days,
                      history_start=str(first.date()), history_end=str(self.last.date())),
                      baseline=dict(gp=baseline_gp, revenue=baseline_revenue,
                                    baskets=float(bweights.sum())),
                      evidence=["Observed: transactions, paid revenue, recorded product costs, basket composition and clock time.",
                                "Projected: weekday averages over the selected history, reweighted to the planning dates; zero-sale calendar days included.",
                                "Assumed: observed 07:00–24:00 coverage represents operating hours; no measured roster or closure log.",
                                "User inputs describe responses, not measured causal effects. Sensitivities are scenarios, not confidence intervals."],
                      caveats=["Historical replay at unchanged weekday demand and product mix; no trend or seasonal extrapolation.",
                               "Gross profit excludes fixed overhead. Only the additional costs entered here are included.",
                               "No supplier invoices or waste logs; recorded unit costs may include accounting allocations.",
                               "Source ends "+str(self.last.date())+". Planning dates do not make these data current."])
        if s['module'] == 'hours':
            result = self._hours(x,s,active_days)
        elif s['module'] == 'combos':
            result = self._combos(x,s,weights)
        else:
            result = self._pricing(x,s)
        common.update(result)
        common['best'] = max(common['rows'],key=lambda r:r['net'])
        common['audit'] = dict(recorded_gp=float(x.gp.sum()),
            recomputed_gp=float((x.revenue-x.line_cost).sum()),
            gp_rounding_difference=float((x.gp-(x.revenue-x.line_cost)).sum()),
            source_lines=len(x), source_baskets=len(b))
        return common

    def _hours(self,x,s,days):
        def row(start,end):
            removed = x[(x.hour < start) | (x.hour >= end)]
            gp = float((removed.gp*removed.weight).sum())
            n = (start-7+24-end)*days
            r = closure(gp,n,s['hourly_saving'],s['recapture'])
            r.update(label=f"{start:02d}:00–{end:02d}:00", start=start,end=end,
                     removed_hours=n, removed_gp=gp)
            return r
        selected = row(s['start_hour'],s['end_hour'])
        rows = [row(start,end) for start in range(7,13) for end in range(18,25)]
        if not any(r['label']==selected['label'] for r in rows): rows.append(selected)
        sensitivity = []
        for capture in sorted(set([0.0,.25,.5,s['recapture']])):
            r = closure(selected['removed_gp'],selected['removed_hours'],s['hourly_saving'],capture)
            sensitivity.append(dict(label=f"{capture:.0%} return at another hour", net=r['net']))
        profile = x.assign(value=x.gp*x.weight).groupby('hour').value.sum().reindex(range(7,24),fill_value=0)
        return dict(rows=sorted(rows,key=lambda r:r['net'],reverse=True), selected=selected,
            sensitivity=sensitivity, chart=[dict(label=f"{h:02d}:00",value=float(v)) for h,v in profile.items()],
            chart_title="Baseline gross profit by hour · selected planning days",
            formula="Δ contribution = removed hours × avoidable cost/hour − removed gross profit × (1 − recapture)",
            assumptions=[f"${s['hourly_saving']:.2f} actually saved per removed branch-hour; fixed wages/rent are excluded.",
                         f"{s['recapture']:.0%} of removed gross profit returns during retained hours, without extra cost or crowding.",
                         "Compare contiguous schedules within observed hours. Grid: open 07–12, close 18–24, plus your selection."],
            next_test="Verify removable roster hours; pilot the schedule on comparable weekdays and track total daily contribution, queues and displaced visits.")

    def _combos(self,x,s,weights):
        x = x[x.hour.between(s['start_hour'],s['end_hour']-1)].copy()
        b = baskets(x)
        groups = x.groupby('product').agg(units=('quantity','sum'), revenue=('revenue','sum'),gp=('gp','sum'))
        lookup = {p:dict(price=float(r.revenue/r.units),gp=float(r.gp/r.units)) for p,r in groups.iterrows()}
        memberships = {p:set(g.transaction) for p,g in x.groupby('product')}
        split = self.first+(self.last-self.first)*2/3
        # Chronological evidence uses all history, but the same branch, weekday and hour scope.
        h = self.x[self.x.branch.eq(s['branch']) & self.x.weekday.isin(s['weekdays'])
                   & self.x.hour.between(s['start_hour'],s['end_hour']-1)]
        train = {p:set(g.transaction) for p,g in h[h.date.le(split)].groupby('product')}
        test = {p:set(g.transaction) for p,g in h[h.date.gt(split)].groupby('product')}
        ntrain=h[h.date.le(split)].transaction.nunique(); ntest=h[h.date.gt(split)].transaction.nunique()
        bw = b.weekday.map(weights).to_dict()
        def weighted(ids): return sum(bw[i] for i in ids)
        def lift(a,b,sets,n):
            aa=sets.get(a,set()); bb=sets.get(b,set())
            return len(aa&bb)*n/(len(aa)*len(bb)) if aa and bb else None
        rows=[]
        for a,c in permutations(groups.index,2):
            if s['anchor']!='Any product' and a!=s['anchor']: continue
            if s['attached']!='Any product' and c!=s['attached']: continue
            aa=memberships[a]; bb=memberships[c]
            existing=weighted(aa&bb); eligible=weighted(aa-bb)
            if not eligible: continue
            pa,pb=lookup[a]['price'],lookup[c]['price']; gb=lookup[c]['gp']
            r=attachment(eligible,existing,s['adoption'],pa,pb,gb,s['combo_discount'],s['extra_cost'])
            tr=len(train.get(a,set())&train.get(c,set())); te=len(test.get(a,set())&test.get(c,set()))
            ltr=lift(a,c,train,ntrain); lte=lift(a,c,test,ntest)
            r.update(label=f"{a} → {c}",anchor=a,attached=c,eligible=eligible,existing=existing,
                     paid_pair_price=pa+pb, offer_price=(pa+pb)*(1-s['combo_discount']),
                     price_a=pa,price_b=pb,gp_b=gb,train_pairs=tr,test_pairs=te,
                     train_lift=ltr,test_lift=lte,
                     evidence="Replicated raw association" if tr>=10 and te>=10 and ltr and lte and ltr>1 and lte>1
                     else "Exploratory · response unmeasured")
            rows.append(r)
        rows.sort(key=lambda r:r['net'],reverse=True)
        noop=dict(label="No offer",net=0.0)
        selected=rows[0] if rows else noop
        sensitivity=[]
        if rows:
            for adoption in sorted(set([0.0,.01,.03,.05,s['adoption']])):
                r=attachment(selected['eligible'],selected['existing'],adoption,selected['price_a'],
                             selected['price_b'],selected['gp_b'],s['combo_discount'],s['extra_cost'])
                sensitivity.append(dict(label=f"{adoption:.0%} extra adoption",net=r['net']))
        return dict(rows=[noop]+rows[:40],selected=selected,sensitivity=sensitivity,
            chart=[dict(label=r['label'],value=r['net']) for r in rows[:8]],
            chart_title="Candidate combos · modeled contribution change",
            formula="Δ contribution = A-only baskets × extra adoption × (B gross profit − pair rebate − extra cost) − existing pair baskets × pair rebate",
            assumptions=[f"{s['adoption']:.1%} of A-only baskets add exactly one B because of the prompt/offer; this is assumed equally across pairs.",
                         f"{s['combo_discount']:.0%} rebate on one A+B pair, relative to historical paid unit prices; existing pair buyers also receive it.",
                         f"${s['extra_cost']:.2f} additional service/waste cost per newly attached unit; no other substitution modeled.",
                         "Direction matters: A is already purchased; B is suggested. Pair lift is raw association, not causal evidence or basket-size-adjusted lift.",
                         "Time window is selected by you. Compare windows manually; the model does not claim to identify optimal promotion timing."],
            next_test="Randomize prompt/no-prompt service blocks. Measure total block contribution, attachment, waits, substitution and stockouts. Compare full-price suggestion before a rebate.")

    def _pricing(self,x,s):
        x = x[x.hour.between(s['start_hour'],s['end_hour']-1)].copy()
        target = x if s['product']=='All products' else x[x['product'].eq(s['product'])]
        revenue=float((target.revenue*target.weight).sum())
        cost=float((target.line_cost*target.weight).sum())
        affected=set(target.transaction)
        other=x[x.transaction.isin(affected) & ~x.index.isin(target.index)]
        other_gp=float((other.gp*other.weight).sum())
        def row(change):
            r=price_scenario(revenue,cost,other_gp,change,s['elasticity'],s['basket_exit'])
            r.update(label=f"{change*100:+g}% price",change=change,affected_revenue=revenue,affected_cost=cost)
            return r
        selected=row(s['price_change'])
        # A true do-nothing policy has no treatment-induced basket exit.
        rows=[dict(label="Keep current prices",net=0.0,change=0.0)]
        rows += [row(c) for c in sorted(set([-.1,-.05,.025,.05,.075,.1,.15,s['price_change']]))]
        sensitivity=[]
        for e in sorted(set([-1.5,-.8,-.25,s['elasticity']])):
            r=price_scenario(revenue,cost,other_gp,s['price_change'],e,s['basket_exit'])
            sensitivity.append(dict(label=f"Elasticity {e:g}",net=r['net']))
        if target.empty:
            selected['net']=0.0
        return dict(rows=sorted(rows,key=lambda r:r['net'],reverse=True), selected=selected,
            sensitivity=sensitivity, chart=[dict(label=r['label'],value=r['net']) for r in rows],
            chart_title="Price alternatives · modeled contribution change",
            formula="Q′/Q = (1 + price change)^elasticity; Δ = [revenue × (1 + change) − costs] × Q′/Q × (1 − basket exit) − old item GP − other affected basket GP × basket exit",
            assumptions=[f"Own-item elasticity {s['elasticity']:g}, supplied as a scenario, not estimated from the CSV.",
                         f"{s['basket_exit']:.1%} additional whole-basket exit after own-item response; this includes the other products in affected baskets once.",
                         "Price change applies to historical effective paid prices, retaining the historical discount mix and fixed unit costs.",
                         "No cross-product substitution or long-term retention effect modeled. The grid winner is conditional, not an optimal real-world price.",
                         f"{target.transaction.nunique()} historical baskets contain the selected products in this time window."],
            next_test="Test a small price change against comparable untreated branch/time blocks. Measure whole-basket contribution, units, substitutions and repeat visits.")

    def _backtest(self):
        daily=self.x.groupby(['branch','date']).gp.sum()
        dates=pd.date_range(self.first,self.last)
        errors_mean=[]; errors_naive=[]; actuals=[]
        for branch in self.branches:
            y=daily.loc[branch].reindex(dates,fill_value=0)
            cutoff=self.last-pd.Timedelta(days=27)
            train=y[y.index<cutoff].tail(56)
            means=train.groupby(train.index.dayofweek).mean()
            for d,actual in y[y.index>=cutoff].items():
                # Fixed origin: repeat the final pre-holdout week, never use holdout actuals.
                reference=cutoff-pd.Timedelta(days=7)+pd.Timedelta(days=(d-cutoff).days%7)
                naive=float(y.get(reference,0))
                predicted=float(means.get(d.dayofweek,0))
                actuals.append(float(actual)); errors_mean.append(abs(predicted-actual));errors_naive.append(abs(naive-actual))
        total=sum(actuals)
        return dict(metric="Daily branch gross profit WAPE",holdout_days=28,
                    holdout_start=str((self.last-pd.Timedelta(days=27)).date()),
                    training_days=56, weekday_mean_wape=sum(errors_mean)/total if total else None,
                    last_week_wape=sum(errors_naive)/total if total else None,
                    note="Fixed-origin chronological check of the baseline only. Not validation of price, offer or closing responses.")
