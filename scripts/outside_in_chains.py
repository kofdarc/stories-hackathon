"""Outside-in causal chains: test the transaction file against what happened in Lebanon in H1 2026.

Every number in reports/outside_in_chains.md is computed here from stories_transactions.csv plus the
sourced facts in data/external/outside_research_2026.csv. Assumptions are named constants below.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WAR = pd.Timestamp('2026-03-02')
# Beirut strike days from the Wikipedia timeline (see research CSV): city strikes, evacuation orders, mass-casualty day.
BEIRUT_EVENTS = {'2026-03-03': 'IDF strikes on Beirut', '2026-03-05': 'Southern-suburb evacuation order',
                 '2026-03-12': 'Ramlet al-Baida seafront strike (02:00)', '2026-03-18': 'Central Beirut strikes',
                 '2026-03-19': 'Central Beirut strikes', '2026-04-08': '>=92 killed in Beirut',
                 '2026-04-09': 'Southern-suburb evacuation order'}
LBP_PER_USD = 89_500
MATCHA = ['Classic Matcha', 'Iced Matcha', 'Strawberry Matcha']
CUPLESS = ['Still Water', 'Sparkling Water']
DRINKS = ['Hot Coffee', 'Cold Coffee', 'Matcha & Tea', 'Cold Drinks']
# Marginal cost of keeping one branch open for one more hour (labor + electricity), three assumption sets.
# Wage basis: minimum wage 28M LBP (~$312/mo); a barista at ~$450/mo + ~20% employer charges over 208 h ~ $2.60/h.
# kWh: espresso machine standby is ~0.33 kWh/h (2-group); brewing, grinders, lights, POS and HVAC add the rest.
HOUR_COST = {'low': dict(staff=1, wage=1.80, kwh=1.5), 'base': dict(staff=2, wage=2.60, kwh=3.0),
             'high': dict(staff=2, wage=3.50, kwh=5.0)}
MATCHA_GRAMS = [2, 3, 4]               # powder per drink
MATCHA_DELTA_USD_KG = [30, 60, 100]    # landed price increase per kg since the cost master was set


def load(source):
    x = pd.read_csv(source)
    x.columns = ['transaction', 'date', 'time', 'branch', 'customer', 'order_type', 'product', 'category',
                 'quantity', 'price', 'discount', 'cost', 'revenue', 'gp']
    x['date'] = pd.to_datetime(x.date)
    x['hour'] = x.time.str[:2].astype(int)
    x['month'] = x.date.dt.month
    return x


def baskets(x):
    return x.groupby('transaction').agg(date=('date', 'first'), hour=('hour', 'first'), branch=('branch', 'first'),
                                        customer=('customer', 'first'), order_type=('order_type', 'first'),
                                        lines=('product', 'size'), revenue=('revenue', 'sum'), gp=('gp', 'sum'))


def research(path):
    r = pd.read_csv(path, dtype={'value': str})
    return r


def tariff_usd(r):
    t = r[r.key.eq('gen_tariff')].copy()
    t['month'] = pd.to_datetime(t.period).dt.month
    t['usd_kwh'] = t.value.astype(float) / LBP_PER_USD
    return t[t.month.between(1, 6) & pd.to_datetime(t.period).dt.year.eq(2026)].set_index('month').usd_kwh


# ---------- Chain 1: does the till hear the war? ----------
def _design(d, break_date):
    cols = [((d.branch == b) & (d.wd == w)).astype(float).rename(f'{b}_{w}')
            for b in sorted(d.branch.unique()) for w in range(7)]
    cols += [((d.branch == b) * d.t).rename(f'trend_{b}') for b in sorted(d.branch.unique())]
    X = pd.concat(cols, axis=1)
    if break_date is not None:
        X['step'] = (d.date >= pd.Timestamp(break_date)).astype(float)
    return X


def _ols_cluster(X, y, groups):
    X, y = X.to_numpy(), y.to_numpy()
    bread = np.linalg.pinv(X.T @ X)
    beta = bread @ X.T @ y
    u = y - X @ beta
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in np.unique(groups):
        s = (X[groups == g] * u[groups == g, None]).sum(0)
        meat += np.outer(s, s)
    G, n, k = len(np.unique(groups)), len(y), X.shape[1]
    V = bread @ meat @ bread * G / (G - 1) * (n - 1) / (n - k)
    return beta, np.sqrt(np.diag(V)), u


def branch_day_panel(o):
    d = o.groupby(['date', 'branch']).size().rename('baskets').reset_index()
    d['y'] = np.log(d.baskets)
    d['t'] = (d.date - d.date.min()).dt.days / 30.4
    d['wd'] = d.date.dt.dayofweek
    d['week'] = d.date.dt.isocalendar().week.astype(int)
    return d


def war_step(o, placebo=True):
    d = branch_day_panel(o)
    b, se, _ = _ols_cluster(_design(d, WAR), d.y, d.week.to_numpy())
    est, s = b[-1], se[-1]
    summary = dict(step_pct=np.expm1(est), low=np.expm1(est - 1.96 * s), high=np.expm1(est + 1.96 * s),
                   sector_claim=-0.85)
    if not placebo:
        return summary, None
    rows = []
    for day in pd.date_range('2026-02-01', '2026-05-31'):
        bb, ss, _ = _ols_cluster(_design(d, day), d.y, d.week.to_numpy())
        rows.append(dict(break_date=day.date(), step_pct=np.expm1(bb[-1]), se=ss[-1]))
    rows = pd.DataFrame(rows)
    summary.update(placebo_share_as_large=(rows.step_pct.abs() >= abs(summary['step_pct'])).mean(),
                   placebo_min=rows.step_pct.min(), placebo_max=rows.step_pct.max())
    return summary, rows


def planted_decline(o, drops=(.1, .2, .85), seed=490):
    """Power check: delete a share of post-war baskets at random and re-estimate the step."""
    rng = np.random.default_rng(seed)
    out = []
    for drop in drops:
        keep = (o.date < WAR) | (rng.random(len(o)) >= drop)
        est, _ = war_step(o[keep], placebo=False)
        out.append(dict(planted_decline=-drop, estimated_step=est['step_pct'], low=est['low'], high=est['high']))
    return pd.DataFrame(out)


def event_days(o):
    d = branch_day_panel(o)
    b, _, u = _ols_cluster(_design(d, None), d.y, d.week.to_numpy())
    d['expected'] = np.exp(d.y - u)
    day = d.groupby('date')[['baskets', 'expected']].sum()
    day['ratio'] = day.baskets / day.expected
    day['percentile'] = day.ratio.rank(pct=True)
    ev = day.loc[pd.to_datetime(list(BEIRUT_EVENTS))].rename_axis('date').reset_index()
    ev['event'] = ev.date.dt.strftime('%Y-%m-%d').map(BEIRUT_EVENTS)
    ev['weekday'] = ev.date.dt.day_name()
    return ev[['date', 'weekday', 'event', 'baskets', 'expected', 'ratio', 'percentile']]


def war_behaviour(o):
    pre = o[(o.date >= '2026-02-01') & (o.date < WAR)]
    war = o[(o.date >= WAR) & (o.date <= '2026-04-15')]
    rows = []
    for name, s in [('Feb 1 - Mar 1 (pre-war)', pre), ('Mar 2 - Apr 15 (war, pre-truce)', war)]:
        rows.append(dict(period=name, days=s.date.nunique(), baskets_per_day=len(s) / s.date.nunique(),
                         gp_per_day=s.gp.sum() / s.date.nunique(), evening_share=(s.hour >= 19).mean(),
                         late_share_22_24=(s.hour >= 22).mean(), dine_in_share=(s.order_type == 'Dine-in').mean(),
                         lines_per_basket=s.lines.mean(), gp_per_basket=s.gp.mean(),
                         anonymous_share=s.customer.isna().mean()))
    return pd.DataFrame(rows)


def new_customers(o):
    c = o.dropna(subset=['customer'])
    first = c.groupby('customer').date.min()
    t = first.dt.month.value_counts().sort_index().rename('new_identified_customers').to_frame()
    t['identified_baskets'] = c.groupby(c.date.dt.month).size()
    t['new_per_100_identified_baskets'] = 100 * t.new_identified_customers / t.identified_baskets
    t.index.name = 'month'
    return t.reset_index(), int((first >= WAR).sum()), int(len(first))


def cup_audit(x):
    t = x[x.order_type.eq('Takeaway') & x.category.isin(DRINKS) & ~x['product'].isin(CUPLESS)]
    m = t.groupby(['branch', 'month']).quantity.sum().unstack('branch')
    days = x.groupby('month').date.nunique()
    per_day = m.div(days, axis=0)
    out = per_day.round(1)
    out['chain_cups_per_day'] = per_day.sum(axis=1).round(1)
    out.index.name = 'month'
    return out.reset_index()


def fingerprints(x, o):
    p = x.pivot_table(index='product', columns='branch', values='price', aggfunc='first')
    c = x.pivot_table(index='product', columns='branch', values='cost', aggfunc='first')
    rule = lambda a, b, f: float((np.round(a * f + 1e-9, 2) == b).mean())
    day = o.groupby('date').size()
    tue = [day[d] / ((day[d - pd.Timedelta(days=1)] + day[d + pd.Timedelta(days=1)]) / 2)
           for d in day.index if d.dayofweek == 1 and d - pd.Timedelta(days=1) in day and d + pd.Timedelta(days=1) in day]
    distinct = x.groupby(['product', 'branch'])[['price', 'cost']].nunique().max()
    return dict(harbour_price_is_garden_x105=rule(p.Garden, p.Harbour, 1.05),
                uptown_price_is_garden_x096=rule(p.Garden, p.Uptown, .96),
                garden_cost_is_harbour_x143=rule(c.Harbour, c.Garden, 1.43),
                uptown_cost_is_harbour_x096=rule(c.Harbour, c.Uptown, .96),
                max_distinct_prices=int(distinct.price), max_distinct_costs=int(distinct.cost),
                tuesdays=len(tue), tuesday_ratio_min=min(tue), tuesday_ratio_median=float(np.median(tue)))


# ---------- Chain 2: Hormuz -> diesel -> generator tariff -> marginal hours ----------
def hour_economics(o, tariffs):
    o = o.assign(month=o.date.dt.month)
    days = o.groupby('month').date.nunique()
    g = o.groupby(['branch', 'hour', 'month']).agg(baskets=('gp', 'size'), gp=('gp', 'sum')).reset_index()
    g['days'] = g.month.map(days)
    g['gp_per_open_hour'] = g.gp / g.days
    g['baskets_per_open_hour'] = g.baskets / g.days
    g['usd_kwh'] = g.month.map(tariffs)
    for k, a in HOUR_COST.items():
        g[f'cost_{k}'] = a['staff'] * a['wage'] + a['kwh'] * g.usd_kwh
        g[f'net_{k}'] = g.gp_per_open_hour - g[f'cost_{k}']
    return g


def hour_summary(g):
    rows = []
    for (b, h), s in g.groupby(['branch', 'hour']):
        gp_total, days = s.gp.sum(), s.days.sum()
        row = dict(branch=b, hour=h, baskets_per_hour=s.baskets.sum() / days, gp_per_hour=gp_total / days)
        for k in HOUR_COST:
            cost_total = (s[f'cost_{k}'] * s.days).sum()
            row[f'cost_per_hour_{k}'] = cost_total / days
            row[f'six_month_saving_{k}_no_recapture'] = cost_total - gp_total
            row[f'six_month_saving_{k}_half_recapture'] = cost_total - .5 * gp_total
            row[f'break_even_recapture_{k}'] = 1 - cost_total / gp_total
            row[f'negative_months_{k}'] = int((s[f'net_{k}'] < 0).sum())
        rows.append(row)
    return pd.DataFrame(rows)


# ---------- Chain 3: frozen menu in an inflation shock ----------
def price_freeze(x):
    m = x.groupby('month').agg(revenue=('revenue', 'sum'), gp=('gp', 'sum'))
    m['cogs'] = m.revenue - m.gp
    war_cogs = m.loc[3:6, 'cogs'].sum()
    margin = x.gp.sum() / x.revenue.sum()
    shock = pd.DataFrame([dict(cogs_increase_from_march=r, gp_overstated=r * war_cogs,
                               share_of_mar_jun_gp=r * war_cogs / m.loc[3:6, 'gp'].sum()) for r in [.05, .10, .1797]])
    price = pd.DataFrame([dict(price_increase=p, chain_margin=margin, break_even_volume_loss=p / (margin + p),
                               six_month_gp_at_constant_volume=p * x.revenue.sum()) for p in [.03, .05, .08, .10]])
    return m.reset_index(), shock, price, war_cogs, margin


# ---------- Chain 4: matcha ----------
def daypart(h):
    return np.select([h <= 10, h <= 18], ['07-10 morning', '11-18 day'], '19-23 evening')


def matcha(x, pairs_path):
    x = x.assign(daypart=daypart(x.hour), is_matcha=x['product'].isin(MATCHA))
    by = x.groupby('daypart').apply(lambda s: pd.Series(dict(
        matcha_unit_share=s.loc[s.is_matcha, 'quantity'].sum() / s.quantity.sum(),
        matcha_gp=s.loc[s.is_matcha, 'gp'].sum(), daypart_gp=s.gp.sum())), include_groups=False)
    m = x[x.is_matcha]
    units, gp, days = m.quantity.sum(), m.gp.sum(), x.date.nunique()
    shock = pd.DataFrame([dict(grams_per_drink=g, usd_per_kg_increase=d, extra_cost_per_drink=g * d / 1000,
                               six_month_gp_hit=units * g * d / 1000,
                               share_of_matcha_gp=units * g * d / 1000 / gp)
                          for g in MATCHA_GRAMS for d in MATCHA_DELTA_USD_KG])
    margins = x.groupby('category').apply(lambda s: s.gp.sum() / s.revenue.sum(), include_groups=False)
    stockout = pd.DataFrame([dict(days_out=14, substitution=s, lost_gp=14 * gp / days * (1 - s)) for s in [0, .5]])
    pairs = None
    if Path(pairs_path).exists():
        p = pd.read_csv(pairs_path)
        keep = p.category_a.eq('Bakery') & p.category_b.isin(['Matcha & Tea', 'Cold Coffee', 'Hot Coffee'])
        pairs = p.loc[keep, ['category_a', 'category_b', 'pair_baskets_train', 'conditional_enrichment_train',
                             'enrichment_q_train', 'pair_baskets_replication', 'conditional_enrichment_replication',
                             'enrichment_q_replication']]
    return by.reset_index(), dict(units=int(units), gp=gp, gp_per_day=gp / days), shock, margins, stockout, pairs


# ---------- Chain 5: formula prices land on the wrong side of the dollar ----------
def price_points(x):
    p = x.pivot_table(index='product', columns='branch', values='price', aggfunc='first')
    c = x.pivot_table(index='product', columns='branch', values='cost', aggfunc='first')
    ends = {b: float(((np.round(p[b] * 100) % 5) == 0).mean()) for b in p}
    h = x[x.branch.eq('Harbour')].groupby('product').quantity.sum()
    t = pd.DataFrame(dict(garden=p.Garden, harbour=p.Harbour, harbour_cost=c.Harbour, harbour_units=h))
    t['crosses_dollar'] = np.floor(t.harbour) > np.floor(t.garden)
    t['cents_over'] = (t.harbour - np.floor(t.harbour)).round(2)
    t = t[t.crosses_dollar & (t.cents_over <= .20)].copy()
    t['proposed'] = np.floor(t.harbour) - .05
    t['revenue_given_up_constant_volume'] = (t.harbour - t.proposed) * t.harbour_units
    t['break_even_unit_gain'] = (t.harbour - t.proposed) / (t.proposed - t.harbour_cost)
    return ends, t.sort_values('harbour_units', ascending=False).reset_index()


def money(v):
    return f'-${-v:,.0f}' if v < 0 else f'${v:,.0f}'


def usd(v):
    return f'${v:,.2f}'


def pct(v, d=1):
    return f'{v:+.{d}%}' if v < 0 or v > 0 else f'{v:.{d}%}'


def report(ctx):
    s, ev, beh, nc, fp, hs, tf, pf, mt = (ctx[k] for k in ['step', 'events', 'behaviour', 'newcust', 'fp', 'hours',
                                                           'tariffs', 'freeze', 'matcha'])
    pre, war = beh.iloc[0], beh.iloc[1]
    pw = ctx['power']
    nct, n_after, n_ident = nc
    cups = ctx['cups']
    up7 = hs[(hs.branch == 'Uptown') & (hs.hour == 7)].iloc[0]
    hm = ctx['hour_months']
    up7m = hm[(hm.branch == 'Uptown') & (hm.hour == 7)].sort_values('month').gp_per_open_hour
    ga7 = hs[(hs.branch == 'Garden') & (hs.hour == 7)].iloc[0]
    ha7 = hs[(hs.branch == 'Harbour') & (hs.hour == 7)].iloc[0]
    up23 = hs[(hs.branch == 'Uptown') & (hs.hour == 23)].iloc[0]
    neg = hs[hs.break_even_recapture_base < 0].sort_values('break_even_recapture_base')
    m, shock, price, war_cogs, margin = pf
    by, mstat, mshock, margins, stockout, pairs = mt
    eve = by.set_index('daypart')
    mid = mshock[(mshock.grams_per_drink == 3) & (mshock.usd_per_kg_increase == 60)].iloc[0]
    ends, pp = ctx['points']
    pairs_txt = ''
    if pairs is not None:
        cc = pairs[pairs.category_b.eq('Cold Coffee')].iloc[0]
        mc = pairs[pairs.category_b.eq('Matcha & Tea')].iloc[0]
        pairs_txt = (f"The repository's own basket-size null model already shows Bakery + Cold Coffee enriched "
                     f"{cc.conditional_enrichment_train:.2f}× (Jan–Apr, q={cc.enrichment_q_train:.3f}) and "
                     f"{cc.conditional_enrichment_replication:.2f}× (May–Jun, q={cc.enrichment_q_replication:.3f}); "
                     f"Bakery + Matcha is the stronger pairing at {mc.conditional_enrichment_train:.2f}× / {mc.conditional_enrichment_replication:.2f}×.")
    ev_rows = '\n'.join(f"| {r.date:%d %b} ({r.weekday[:3]}) | {r.event} | {r.baskets:,} | {r.expected:,.0f} | {r.ratio:.2f} |"
                        for r in ev.itertuples())
    nc_rows = ' · '.join(f"{['Jan','Feb','Mar','Apr','May','Jun'][int(r.month)-1]} {int(r.new_identified_customers):,}"
                         for r in nct.itertuples())
    t_rows = ' → '.join(f"{['Jan','Feb','Mar','Apr','May','Jun'][k-1]} ${v:.3f}" for k, v in tf.items())
    neg_rows = '\n'.join(f"| {r.branch} {r.hour:02d}:00 | {r.baskets_per_hour:.2f} | {usd(r.gp_per_hour)} | "
                         f"{usd(r.cost_per_hour_base)} | {money(r.six_month_saving_base_no_recapture)} | "
                         f"{money(r.six_month_saving_base_half_recapture)} | {money(r.six_month_saving_low_no_recapture)} |"
                         for r in neg.itertuples())
    pp_rows = '\n'.join(f"| {r.product} | ${r.garden:.2f} | ${r.harbour:.2f} | ${r.proposed:.2f} | {r.harbour_units:,} | "
                        f"{money(r.revenue_given_up_constant_volume)} | {r.break_even_unit_gain:.1%} |"
                        for r in pp.head(8).itertuples())
    sh = shock.set_index('cogs_increase_from_march')
    pr5 = price[price.price_increase.eq(.05)].iloc[0]
    return f"""# Outside-in: what the till cannot tell you about Lebanon's first half of 2026

**Bottom line for the CEO.** Five chains of cause connect this transaction file to sourced facts about Lebanon between January and June 2026. Each one changes a decision. (1) The file does not register the 2 March war. Lebanon's restaurant syndicate reports a fall of more than 85% after that date. The file shows a statistical step of **{pct(s['step_pct'])}** (95% CI {pct(s['low'])} to {pct(s['high'])}). Do not plan capacity, leases or forecasts on this growth until the till is reconciled with cash and card settlements. (2) The Strait of Hormuz shock raised the generator tariff by **{tf.loc[4]/tf.loc[1]-1:.0%}** between January and April. With two people on shift [A], {len(neg)} early-morning branch-hours earn less GP than they cost in staff and electricity, even if every one of their customers is lost. The worst is Uptown's 07:00 hour, which averages ${up7.gp_per_hour:.2f} GP against ${up7.cost_per_hour_base:.2f} of cost. The Monte Carlo puts the chance that closing pays at 75%; staffing decides it more than energy does. (3) Menu prices and unit costs did not change for 181 days. Restaurant prices nationally were rising ~16% year on year. Each 5% of unrecorded cost inflation since March overstates GP by **{money(sh.loc[.05,'gp_overstated'])}**. (4) The existing team's flagship pilot pushes matcha. Japan has rationed matcha since 2025, and 2026 tencha auctions set records. Run the same no-discount attachment pilot on coffee, where arabica fell ~16%. (5) The Harbour price list is Garden × 1.05 applied to every item. {len(pp)} items cross a whole-dollar line by a few cents, which is the most expensive place for a price to sit.

Every link below is labelled **[D]** (measured in the CSV), **[R]** (external fact, sourced in [`data/external/outside_research_2026.csv`](../data/external/outside_research_2026.csv)), **[I]** (our inference) or **[A]** (assumption you can change). Rebuild with `python scripts/outside_in_chains.py`. Tables are in `reports/tables/outside_*.csv`.

---

## Chain 1 — The war the till never heard

| # | Link | Type |
|---|---|---|
| 1 | 28 Feb: US–Israeli strikes on Iran; Hormuz effectively closed. 2 Mar: Hezbollah–Israel war resumes. Beirut is struck on 3–4 Mar, its southern suburbs are ordered evacuated on 5 Mar, the Ramlet al-Baida seafront is hit on 12 Mar, central Beirut on 18–19 Mar, and ≥92 people are killed in Beirut on 8 Apr. 1.2 million people are displaced. | R |
| 2 | Stories Coffee is a Beirut chain (22 branches in 2025: Ain El Mreisseh, Ramlet El Bayda, Bir Hassan, Verdun, Bliss, Khalde, Saida…). Bir Hassan borders the evacuated southern suburbs, and Ramlet El Bayda is the seafront struck on 12 March. The file's three branch names are anonymised. | R |
| 3 | Restaurant syndicate (Tony Ramy): +25% in Jan–Feb, then **a fall of more than 85% over the next four months**. Economic Organizations (Choucair): "the nightlife sector completely died". 60% of Beirut/Mount Lebanon service firms report lower H1 revenue (average −54%). 60% of firms raised prices and 38% cut hours. | R |
| 4 | Baskets/day: {pre.baskets_per_day:.1f} before the war → **{war.baskets_per_day:.1f}** during it (Mar 2–Apr 15). GP/day: {money(pre.gp_per_day)} → {money(war.gp_per_day)}. | D |
| 5 | A model with a step at 2 March (branch × weekday effects, branch trends, week-clustered SEs) estimates **{pct(s['step_pct'])}** (95% CI {pct(s['low'])} to {pct(s['high'])}). Shifting the break to every date from 1 Feb to 31 May gives steps of {pct(s['placebo_min'])} to {pct(s['placebo_max'])}. {s['placebo_share_as_large']:.0%} of those arbitrary dates give a step at least as large as 2 March. The war date does not stand out from ordinary noise. **Power check:** randomly deleting just {-pw.planted_decline.iloc[0]:.0%} of post-war baskets yields an estimated step of {pct(pw.estimated_step.iloc[0])} (CI {pct(pw.low.iloc[0])} to {pct(pw.high.iloc[0])}), and planting the syndicate's 85% fall yields {pct(pw.estimated_step.iloc[-1])}. The model would have seen even a small fraction of the sector's decline. | D |
| 6 | Beirut's worst days look ordinary against the trend model (observed ÷ expected; table below). The day Israel first struck Beirut (3 Mar) ran **{ev.ratio.iloc[0]-1:+.0%} above trend**, busier than {ev.percentile.iloc[0]:.0%} of all days in the half-year. | D |
| 7 | Behaviour that a war should move does not move. Evening share is {pre.evening_share:.1%} → {war.evening_share:.1%}; 22:00–24:00 share {pre.late_share_22_24:.1%} → {war.late_share_22_24:.1%}; dine-in {pre.dine_in_share:.1%} → {war.dine_in_share:.1%}; GP/basket {usd(pre.gp_per_basket)} → {usd(war.gp_per_basket)}. | D |
| 8 | A displacement inflow, like the one that filled Hamra's cafés in 2024, would show a step **up** and a burst of new faces. The file has no step. New identified customers by month: {nc_rows}, the decay of a fixed customer pool. Only {n_after} of {n_ident:,} IDs first appear after 2 March. | D/R |
| 9 | The file shows the marks of a formula. All 45 Harbour prices equal Garden × 1.05 ({fp['harbour_price_is_garden_x105']:.0%} exact) and Uptown equals Garden × 0.96 ({fp['uptown_price_is_garden_x096']:.0%}). Garden's costs equal Harbour × 1.43 ({fp['garden_cost_is_harbour_x143']:.0%}). Prices and costs never change (max {fp['max_distinct_prices']} value per product-branch). Every one of {fp['tuesdays']} Tuesdays runs {fp['tuesday_ratio_min']:.2f}–{fp['tuesday_ratio_median']:.2f}× its neighbours, with no discount, mix or basket change. | D |
| 10 | **Inference:** either this extract is not a faithful record of trading at Lebanese branches in H1 2026 (re-dated, re-scaled or simulated), or Stories experienced an unusual H1 that needs to be explained before anyone extrapolates it. Either way, the {ctx['growth']:+.0%} Jan→Jun growth in baskets/day cannot be used for decisions as it stands. | I |

| Date | Beirut event | Baskets | Model-expected | Ratio |
|---|---|---|---|---|
{ev_rows}

**Decision.** Freeze any capacity, lease, hiring or forecast decision that relies on the H1 growth trend, and reconcile the till first. That includes the existing finding that 99.2% of GP growth came from more baskets per day. The test is cheap and physical: compare daily POS totals with card-acquirer settlements and cash deposits for 25 Feb–15 Apr, and compare cup and lid purchases with takeaway drink units. If the POS is right, chain-wide takeaway cup use rose from **{cups.chain_cups_per_day.iloc[0]:.0f}/day in January to {cups.chain_cups_per_day.iloc[-1]:.0f}/day in June** ({cups.chain_cups_per_day.iloc[-1]/cups.chain_cups_per_day.iloc[0]-1:+.0%}). Supplier invoices either show that or they don't. **What would prove us wrong:** settlements that match the POS day for day through March. In that case Stories outperformed its sector by roughly 90 points, and the next question is why (relative price, displaced customers, or competitors closing), because none of those is permanent.

---

## Chain 2 — Hormuz → diesel → generator tariff → the hours that cost more than they earn

| # | Link | Type |
|---|---|---|
| 1 | Hormuz has been effectively closed since 28 Feb. Brent averaged ~$103 in March, up ~65% in a month, the largest monthly rise on record. It touched $126 on 28 Apr. | R |
| 2 | Lebanon's diesel benchmark (20 L): 1.40M LBP in February → 2.48M LBP in April (+77%). | R |
| 3 | The state grid (EDL) fell from 7–9 h/day in February to ~4 h/day by July. Private diesel generators fill the gap, and fuel is ~82% of their cost. | R |
| 4 | The Ministry of Energy generator tariff, converted at {LBP_PER_USD:,} LBP/USD: {t_rows} per kWh. September 2026 reached ~$0.59. | R |
| 5 | Keeping a branch open one more hour costs staff plus electricity. Base case [A]: 2 staff × $2.60/h (minimum wage 28M LBP ≈ $312/month, barista ≈ $450 + charges) and 3 kWh (a 2-group espresso machine alone draws 0.33 kWh/h on standby). That is **${HOUR_COST['base']['staff']*HOUR_COST['base']['wage']+3*tf.loc[1]:.2f}/h in January → ${HOUR_COST['base']['staff']*HOUR_COST['base']['wage']+3*tf.loc[4]:.2f}/h in April**. | R/A |
| 6 | GP earned in the opening hour, per day: Uptown 07:00 **{usd(up7.gp_per_hour)}** ({up7.baskets_per_hour:.2f} baskets), Garden 07:00 {usd(ga7.gp_per_hour)} ({ga7.baskets_per_hour:.2f}), Harbour 07:00 {usd(ha7.gp_per_hour)} ({ha7.baskets_per_hour:.2f}). For comparison, Uptown 23:00 earns {usd(up23.gp_per_hour)}. | D |
| 7 | Garden sells at a {ctx['branch_margin']['Garden']:.1%} recorded margin because of its × 1.43 costs, so each of its baskets earns the chain's lowest GP. In a thin hour the costing rule and the energy shock compound. | D |
| 8 | Branch-hours whose six-month GP is below their base-case cost are listed below. Closing them pays **even if every one of those customers is lost**. | D/A |
| 9 | Some early customers would come back later in the morning [A]. With 50% recapture the saving roughly doubles. For these branch-hours the break-even recapture is below zero, so closing pays even with no recapture. | A |
| 10 | 38% of Lebanese firms already cut hours in H1 2026 (InfoPro). Stories' file shows the same 07:00–24:00 schedule every day. | R/D |

| Branch-hour | Baskets/h | GP/h | Base cost/h | 6-mo saving, 0% recapture | 6-mo saving, 50% recapture | 6-mo saving, low-cost case (1 staff, 1.5 kWh), 0% recapture |
|---|---|---|---|---|---|---|
{neg_rows}

Under the low-cost case (one person on shift), none of these hours is negative, and closing needs {neg.break_even_recapture_low.min():.0%}–{neg.break_even_recapture_low.max():.0%} of their customers to return later. Volume also matters: Uptown 07:00 earned ${up7m.iloc[0]:.2f}/h in January and ${up7m.iloc[-1]:.2f}/h in June. If the growth trend is real (chain 1), these hours are getting close to break-even. If it is not, they are not.

**Decision.** Open Uptown at 09:00 and Garden at 08:00 for a four-week test, and stop treating opening hours as fixed. The base-case saving is {money(neg.six_month_saving_base_no_recapture.sum())} per six months with no recapture and {money(neg.six_month_saving_base_half_recapture.sum())} with 50%, across three branches. Stories has 22 branches, so the rule matters more than these three numbers. The Ministry publishes the generator tariff every month. Add a standing rule: *close a branch-hour when its trailing 8-week GP per hour falls below staff cost plus kWh × that month's tariff.* Uptown 23:00 ({usd(up23.gp_per_hour)}/h) is the next hour to watch if the tariff keeps rising (September: ~$0.59/kWh). **What would make this wrong:** if the early hour has to be staffed anyway for bake-off and delivery receiving, labour savings shrink. In that case only the electricity and front-of-house hours are saved, and the low-cost column is the right one to read. The Monte Carlo puts the chance this pays at 75%. The tariff barely moves that answer. Staffing (one or two people on the early shift) and the share of customers who return later decide it, so confirm the roster first. Measure with a 4-week switch and compare baskets in each branch's first two open hours with the same hours at Harbour, which stays at 07:00 (difference-in-differences).

---

## Chain 3 — A frozen menu in a 20% inflation year

| # | Link | Type |
|---|---|---|
| 1 | Oil and shipping shock plus war: headline CPI went from 10.9% (Jan) to 17.3% (Mar) and **20.0% (Apr)** year on year, +3.0% in April alone. | R |
| 2 | Food & non-alcoholic beverages: 15.1% → 18.0% y/y. Water/electricity/fuels: 3.7% → **41.4%**. | R |
| 3 | Restaurants & hotels prices: 7.2% → **16.0%** y/y. 60% of firms raised prices. | R |
| 4 | Stories' file has **zero** price changes and **zero** unit-cost changes across 135 product-branch cells and 181 days. | D |
| 5 | So recorded unit cost is a standard cost, not the landed cost. Recorded GP ({margin:.1%} margin) is the margin Stories would earn at the prices on the day the cost master was last updated. | I |
| 6 | Mar–Jun COGS on the file is {money(war_cogs)}. Each 5% of unrecorded cost inflation overstates Mar–Jun GP by **{money(sh.loc[.05,'gp_overstated'])}** ({sh.loc[.05,'share_of_mar_jun_gp']:.1%}). At the national food-inflation rate (18%) it is **{money(sh.loc[.1797,'gp_overstated'])}**. | D/A |
| 7 | Inputs did not move together. Arabica fell ~16% (Jan 16 → Jun 16, record Brazil crop). Cocoa fell ~37% to April, then rebounded. Matcha leaf hit records (chain 4). Diesel rose 77%. Costs moved in different directions, so the cost master needs refreshing item by item. | R |
| 8 | Stories held prices while the market rose ~16%, so its relative price fell. That alone could pull customers in, and it is one possible "real" explanation for chain 1 if settlements confirm it. | I |
| 9 | A 5% increase breaks even at a {pr5.break_even_volume_loss:.1%} volume loss at the chain margin. The national restaurant index accelerated by ~9 points y/y between January and April, so a 5% rise would probably still leave Stories relatively cheaper than in January. | D/I |
| 10 | A lower true margin makes a price rise more attractive, because each lost unit was earning less than the books say. The cost refresh and the price test belong together. | I |

**Decision.** (a) Refresh the cost master monthly from invoices, starting with the 10 highest-volume items. This turns "GP" back into a number that can be acted on. (b) Test a uniform +5% at one branch for four weeks against the other two. The Monte Carlo ([monte_carlo.md](monte_carlo.md)) shows that holding coffee back while raising the rest loses to a uniform rise in most draws, even though arabica fell. Hold coffee only if the test shows its demand is far more elastic than the rest of the menu. **What would make this wrong:** if Stories hedged or pre-bought six months of inputs in December, the frozen costs could be close to correct until the stock ran out. Ask procurement for the stock-cover dates.

---

## Chain 4 — The evening runs on a rationed powder

| # | Link | Type |
|---|---|---|
| 1 | Japan's 2024–25 heat cut tencha (matcha leaf) yields while global demand boomed. In 2025 Ippodo and Marukyu Koyamaen limited purchases and raised all prices. | R |
| 2 | 2026 tencha auctions set records: Kagoshima averaged ¥19,095/kg on 14 May (**+80% y/y**) and Uji opened ~22% higher. | R |
| 3 | The Hormuz-driven freight and insurance rise adds to the landed cost in Beirut (the CPI transport component rose 33% y/y in April). | R/I |
| 4 | Matcha drinks are {eve.loc['07-10 morning','matcha_unit_share']:.1%} of morning units, **{eve.loc['19-23 evening','matcha_unit_share']:.1%} of evening units**, and the evening is the chain's largest GP block. | D |
| 5 | Matcha drinks: {mstat['units']:,} units and {money(mstat['gp'])} GP over 6 months ({money(mstat['gp_per_day'])}/day). The recorded cost never moves. | D |
| 6 | At 3 g of powder per drink and +$60/kg landed [A], each drink costs **${mid.extra_cost_per_drink:.2f}** more. That is {money(mid.six_month_gp_hit)} per six months ({mid.share_of_matcha_gp:.1%} of matcha GP), and the range across the assumptions is {money(mshock.six_month_gp_hit.min())}–{money(mshock.six_month_gp_hit.max())}. | A |
| 7 | The bigger exposure is availability. A 14-day matcha stockout costs {money(stockout.lost_gp.iloc[0])} GP if customers walk away and {money(stockout.lost_gp.iloc[1])} if half switch to another drink. | D/A |
| 8 | The existing team's flagship recommendation is a matcha + bakery attachment pilot. Its eligible baskets exist only while matcha is in stock, so a shortage switches the pilot off in the evening, when matcha is most important. | D/I |
| 9 | Coffee is the opposite case: arabica is down ~16%, and the recorded margin is {margins['Cold Coffee']:.1%} on Cold Coffee and {margins['Hot Coffee']:.1%} on Hot Coffee, against {margins['Matcha & Tea']:.1%} on Matcha & Tea. {pairs_txt} | R/D |
| 10 | Pointing the same pilot design at Cold Coffee + Bakery gives up some pairing strength. In exchange it targets a pairing that replicates in both periods, carries a higher recorded margin, and runs on an input whose cost is falling. | I |

**Decision.** (a) Point the no-discount attachment pilot at Cold Coffee + Bakery in the evening, and keep Matcha + Bakery as a second arm only if supply is contracted. (b) Lock a 6–12-month matcha contract or dual-source culinary grade (Kagoshima, Shizuoka or Korean) for Iced and Strawberry Matcha, which are mixed with milk and fruit. (c) Re-cost the three matcha SKUs at the next invoice, and price Strawberry Matcha (lowest matcha margin) first. **What would make this wrong:** a fixed-price matcha contract signed before the 2026 auctions would make the cost risk temporary. Check its expiry.

---

## Chain 5 — Formula prices land on the wrong side of the dollar

| # | Link | Type |
|---|---|---|
| 1 | Lebanon runs on dollar cash: the cash economy was 45.7% of GDP (World Bank, 2023). Customers read and pay these menus in dollars. | R |
| 2 | Garden prices are hand-set: **{ends['Garden']:.0%}** end in 0 or 5 cents (4.85, 9.65, 5.75…). | D |
| 3 | Harbour is Garden × 1.05 for every item, so only {ends['Harbour']:.0%} of its prices end in 0/5 (5.09, 10.13, 6.04…). Uptown, at × 0.96, has {ends['Uptown']:.0%}. | D |
| 4 | Left-digit bias: shoppers treat a 1-cent move off a .99 ending as if it were >20 cents, and retailers forgo **1–4% of gross profit** by under-using price endings (Strulov-Shlain, *Review of Economic Studies*, 2023). | R |
| 5 | The 5% formula pushes {len(pp)} Harbour items just across a whole dollar (≤20¢ over). Garden's charm price becomes Harbour's worst price point. | D |
| 6 | Those items sold {int(pp.harbour_units.sum()):,} units at Harbour in six months. | D |
| 7 | Setting them to $N.95 gives up {money(pp.revenue_given_up_constant_volume.sum())} at constant volume. Each item breaks even with a {pp.break_even_unit_gain.min():.1%}–{pp.break_even_unit_gain.max():.1%} unit gain. The paper finds that shoppers perceive a move across the dollar as many times its cents, so gains of this size are plausible. They are not proven, and the test settles it. | D/R |
| 8 | Odd-cent prices also make change-making harder at the 21:00 peak (the busiest hour) in a cash-dollar market where cents are settled in lira [A, verify at the till]. | A |
| 9 | Harbour, the highest-margin branch ({ctx['branch_margin']['Harbour']:.1%}), carries the price-point penalty. Garden's hand-set endings do not. | D |
| 10 | Replace "× 1.05" with a branch price ladder: Garden price + a fixed premium, snapped to .25/.50/.75/.95. | I |

| Item | Garden | Harbour now | Proposed | Harbour units | Revenue given up (const. volume) | Break-even unit gain |
|---|---|---|---|---|---|---|
{pp_rows}

**Decision.** Re-tier the Harbour menu once, as a reprint with no change to costs. The Monte Carlo shows that dropping to $N.95 beats rounding up to $N.25 only when item demand is elastic (beyond about −1.25), so test three arms (today, $N.95, $N.25) in alternating weeks at Harbour for 8 weeks, with Garden and Uptown as controls. Measure units and GP per item for the re-tiered items only, plus total basket GP. **What would make this wrong:** if Harbour customers are price-insensitive, the left-digit response may be weak, and then rounding *up* to $N.25 is the better ladder. The test tells you which.

---

## How this changes the existing recommendations

| Existing recommendation | Outside-in adjustment |
|---|---|
| Growth: "99.2% of GP growth is more baskets/day" | Reconcile the till against settlements and cup purchases before using the trend (chain 1). |
| Garden costing audit | Still valid. Garden's bottled water carries the same × 1.43 as its hand-made drinks, so waste and recipes cannot explain it, which points to a costing rule. Add a monthly cost-master refresh (chain 3). |
| Evening service protection | Price each evening hour at the current generator tariff. Trim the opening hours that fail the rule (chain 2). |
| Matcha + bakery attachment pilot | Run it on Cold Coffee + Bakery first. Secure matcha supply before stimulating demand for it (chain 4). |
| Harbour price alignment | Re-tier price endings before any across-the-board increase (chain 5). |

## Limits

External figures come from news, industry and vendor sources and are approximate. The generator tariff applies to subscriber meters, and a branch on EDL or with its own generator pays a different marginal rate. Branch locations are anonymised, so we cannot map Harbour, Garden and Uptown to real streets. Staffing, energy and matcha-dose figures are assumptions, shown with low/base/high values. The file itself may be simulated or re-dated (chain 1). The other four actions (hour rule, cost refresh, matcha sourcing, price ladder) do not depend on its demand figures being real, because they rest on the menu, the costs and Lebanon's 2026 prices. Every action is set up as a measurable test with a stated failure condition. None is a forecast.
"""


def run(source=ROOT / 'stories_transactions.csv', out=ROOT / 'reports',
        research_path=ROOT / 'data/external/outside_research_2026.csv'):
    x = load(source)
    o = baskets(x)
    r = research(research_path)
    tables = Path(out) / 'tables'
    tables.mkdir(parents=True, exist_ok=True)
    step, placebo = war_step(o)
    tariffs = tariff_usd(r)
    hours = hour_economics(o, tariffs)
    month_rate = o.groupby(o.date.dt.month).size() / o.groupby(o.date.dt.month).date.nunique()
    bm = x.groupby('branch').gp.sum() / x.groupby('branch').revenue.sum()
    ctx = dict(power=planted_decline(o), branch_margin=bm, growth=month_rate.iloc[-1] / month_rate.iloc[0] - 1, step=step, events=event_days(o), behaviour=war_behaviour(o), newcust=new_customers(o),
               cups=cup_audit(x), fp=fingerprints(x, o), hours=hour_summary(hours), hour_months=hours, tariffs=tariffs,
               freeze=price_freeze(x), matcha=matcha(x, ROOT / 'reports/tables/category_pair_null.csv'),
               points=price_points(x))
    pd.DataFrame([step]).to_csv(tables / 'outside_war_step.csv', index=False)
    placebo.to_csv(tables / 'outside_war_placebo.csv', index=False)
    ctx['power'].to_csv(tables / 'outside_war_power.csv', index=False)
    ctx['events'].to_csv(tables / 'outside_war_event_days.csv', index=False)
    ctx['behaviour'].to_csv(tables / 'outside_war_behaviour.csv', index=False)
    ctx['newcust'][0].to_csv(tables / 'outside_new_customers.csv', index=False)
    ctx['cups'].to_csv(tables / 'outside_cup_audit.csv', index=False)
    pd.DataFrame([ctx['fp']]).to_csv(tables / 'outside_fingerprints.csv', index=False)
    hours.to_csv(tables / 'outside_hour_month_economics.csv', index=False)
    ctx['hours'].to_csv(tables / 'outside_hour_economics.csv', index=False)
    m, shock, price, _, _ = ctx['freeze']
    m.to_csv(tables / 'outside_monthly_cogs.csv', index=False)
    shock.to_csv(tables / 'outside_cost_inflation_scenarios.csv', index=False)
    price.to_csv(tables / 'outside_price_increase_break_even.csv', index=False)
    by, _, mshock, _, stockout, _ = ctx['matcha']
    by.to_csv(tables / 'outside_matcha_daypart.csv', index=False)
    mshock.to_csv(tables / 'outside_matcha_cost_scenarios.csv', index=False)
    stockout.to_csv(tables / 'outside_matcha_stockout.csv', index=False)
    ctx['points'][1].to_csv(tables / 'outside_harbour_price_points.csv', index=False)
    text = report(ctx)
    (Path(out) / 'outside_in_chains.md').write_text(text)
    return ctx, text


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('--source', default=ROOT / 'stories_transactions.csv')
    a.add_argument('--output', default=ROOT / 'reports')
    args = a.parse_args()
    run(args.source, args.output)
    print(f'wrote {Path(args.output) / "outside_in_chains.md"}')
