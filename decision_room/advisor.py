"""Business-facing recommendations from a validated sales CSV.

Sales can identify exposure and test candidates. They cannot reveal avoidable
rent/payroll, stock on hand, expiry or a customer's response to a new offer.
"""
from collections import Counter
from io import StringIO

import pandas as pd

from src.analytics import RENAME, load_data, baskets


def read_upload(content):
    try:
        text=content.decode('utf-8-sig')
        raw=pd.read_csv(StringIO(text),dtype={'Transaction ID':'string','Customer ID':'string'})
    except (UnicodeError,pd.errors.ParserError,pd.errors.EmptyDataError):
        raise ValueError('Upload a UTF-8 CSV with one header row. You can download the example format below.') from None
    missing=[c for c in RENAME if c not in raw]
    if missing: raise ValueError('Missing columns: '+', '.join(missing))
    x=load_data(StringIO(raw[list(RENAME)].to_csv(index=False)))
    if x.drop(columns='customer').isna().any().any():
        raise ValueError('Some required values are blank. Only Customer ID may be blank.')
    if (x.quantity<=0).any() or (x.quantity%1!=0).any() or not x.discount.between(0,1).all() or (x[['price','cost','revenue']]<0).any().any():
        raise ValueError('Quantities must be positive whole numbers, money nonnegative, and discount rates between 0 and 1.')
    metadata=x.fillna({'customer':'anonymous'}).groupby('transaction')[['date','time','branch','customer','order_type']].nunique()
    if metadata.gt(1).any().any(): raise ValueError('Some transaction IDs refer to different orders. Give each order a unique transaction ID.')
    if ((x.revenue-x.list_value*(1-x.discount)).abs()>.00501).any() or ((x.gp-(x.revenue-x.line_cost)).abs()>.00501).any():
        raise ValueError('Revenue or gross profit does not match quantity, price, discount and unit cost. Please check those columns.')
    if (x.date.max()-x.date.min()).days>3653:
        raise ValueError('Please upload no more than ten years of sales at once.')
    return x, [c for c in raw if c not in RENAME]


def usd(value,decimals=0): return f'${value:,.{decimals}f}'


def card(key,title,status,action,reason,next_step,details=None,table=None,columns=None):
    return dict(key=key,title=title,status=status,action=action,reason=reason,next_step=next_step,
                details=details or [],table=table or [],columns=columns or [])


def build_report(x,ignored=None):
    if x.empty: raise ValueError('No sales were found in this file.')
    first=x.date.min();last=x.date.max();days=(last-first).days+1
    recent_start=max(first,last-pd.Timedelta(days=55))
    recent=x[x.date.ge(recent_start)].copy()
    rdays=(last-recent_start).days+1
    b=baskets(x)
    branches=x.groupby('branch').agg(revenue=('revenue','sum'),gp=('gp','sum'),orders=('transaction','nunique'))
    branch_rows=[dict(branch=str(name),orders=int(r.orders),revenue=usd(r.revenue),
                      gross_profit=usd(r.gp),gross_profit_per_day=usd(r.gp/days,2),
                      margin=f'{r.gp/r.revenue:.1%}' if r.revenue else '—') for name,r in branches.iterrows()]
    cards=[];hours=[]
    for branch,g in recent.groupby('branch'):
        # Includes all calendar days, not only days with a sale in the target hour.
        profile=g.groupby('hour').gp.sum()/rdays
        opening=int(profile.index.min());last_hour=int(profile.index.max())
        if opening>=last_hour: continue
        early=float(profile.loc[opening]);late=float(profile.loc[last_hour]);peak=int(profile.idxmax())
        edge=opening if early<=late else last_hour
        proposed=f'open at {opening+1:02d}:00 instead of {opening:02d}:00' if edge==opening else f'close at {last_hour:02d}:00 instead of {last_hour+1:02d}:00'
        hours.append(dict(branch=str(branch),candidate=proposed,
            hourly_contribution=usd(float(profile.loc[edge]),2),peak=f'{peak:02d}:00–{peak+1:02d}:00',
            edge_hour=edge,threshold=float(profile.loc[edge])))
    if hours:
        weak=min(hours,key=lambda r:r['threshold'])
        cards.append(card('hours','Opening hours','Test first',
            f"Review {weak['branch']}: {weak['candidate']}.",
            f"That hour brings in about {weak['hourly_contribution']} a day after product costs. Shorter hours pay only if the costs you actually save exceed the profit you lose.",
            'Check whether you can remove paid staff hours and utility costs. Then try the change on comparable weekdays and check total daily profit.',
            ['These are the quieter edge hours, not proven optimal schedules.',
             f'Uses the latest {rdays} calendar days. Sales times suggest opening coverage; actual opening schedules are not provided.',
             'Threshold assumes those sales disappear. Customers returning later could lower the required saving.',
             'Days with no recorded sale are included; missing records and store closures cannot be distinguished.'],
            [{k:r[k] for k in ('branch','candidate','hourly_contribution','peak')} for r in hours],
            ['Branch','Schedule to review','Profit from that hour / day','Busiest profit hour']))
    else:
        cards.append(card('hours','Opening hours','Need more data','Keep the current schedule for now.',
            'There is not enough coverage across different hours to compare schedules.',
            'Add more trading days and your actual opening schedule.'))
    weakest=branches.gp.idxmin()
    cards.append(card('closure','Which branches to close','Need operating costs',
        'Keep branches open until their full costs are checked.',
        f"{weakest} has the lowest recorded gross profit, so review it first. Sales alone do not show whether closing it would save money.",
        'Add avoidable rent, payroll, closure costs and how many customers would move to another branch. Compare keeping, improving and closing the branch.',
        ['Gross profit means sales minus recorded product costs. It does not subtract rent, payroll or other overhead.',
         'Lowest gross profit is a review priority, not evidence that the branch should close.',
         'Branch totals use the full uploaded period, including zero-sale calendar days.'],branch_rows,
        ['Branch','Orders','Revenue','Gross profit','Gross profit / day','Gross margin']))
    product_rows=[]
    for (branch,product),g in recent.groupby(['branch','product']):
        series=g.groupby('date').quantity.sum().reindex(pd.date_range(recent_start,last),fill_value=0)
        product_rows.append(dict(branch=str(branch),item=str(product),daily=float(series.mean()),
            typical=f'{series.quantile(.25):.0f}–{series.quantile(.75):.0f}',
            cost=float(g.line_cost.sum()/g.quantity.sum()),category=str(g.category.mode().iloc[0])))
    restock=[]
    for branch in branches.index:
        for r in sorted([v for v in product_rows if v['branch']==branch],key=lambda v:v['daily'],reverse=True)[:3]:
            restock.append(dict(branch=r['branch'],item=r['item'],daily_units=f"{r['daily']:.1f}",typical=r['typical']))
    cards.append(card('restock','Restocking & preparation','Sales-based starting point',
        'Use recent daily sales to plan preparation, then subtract the stock you already have.',
        'The table shows your fastest-selling items by branch. It helps set a starting quantity, but sales can understate demand when an item runs out.',
        'Add stock on hand, supplier lead times and shelf life before treating these as order quantities.',
        [f'Daily averages and the middle half of observed daily sales use the latest {rdays} days, including zero-sale dates.',
         'These are historical sales guides, not optimized inventory orders or measured stockout probabilities.'],
        restock,['Branch','Item','Average sold / day','Middle half of days']))
    perishable=[r for r in product_rows if any(v in r['category'].lower() for v in ('bakery','dessert','sandwich','salad','food','breakfast'))]
    slow=sorted(perishable,key=lambda r:r['daily'])[:5]
    cards.append(card('waste','Waste management','Need waste records',
        'Check small batches of slower-selling fresh items before adding clearance discounts.',
        'Selling slowly is a reason to inspect preparation quantities. It does not prove that food is being wasted.',
        'Record prepared, sold and discarded quantities with expiry times. Only discount stock that is genuinely at risk of being thrown away.',
        ['Fresh-item candidates are inferred from category names; actual perishability and shelf life are unknown.',
         'No waste savings or expiry-driven discount timing is estimated from sales alone.'],
        [dict(branch=r['branch'],item=r['item'],daily_units=f"{r['daily']:.1f}") for r in slow],
        ['Branch','Fresh item to review','Average sold / day']))
    price_rows=[]
    for branch,g in recent.groupby('branch'):
        revenue=float(g.revenue.sum());gp=float(g.gp.sum())
        new_gp=gp+.05*revenue
        gate=1-gp/new_gp if new_gp>0 else None
        cut_gp=gp-.05*revenue
        extra=gp/cut_gp-1 if cut_gp>0 and gp>0 else None
        price_rows.append(dict(branch=str(branch),increase='+5%',sales_loss_limit=f'{gate:.1%}' if gate is not None else 'Not viable',
                               price_cut_extra_sales=f'{extra:.1%}' if extra is not None else 'Not viable',source_gp=gp,source_revenue=revenue))
    cards.append(card('pricing','Price increases & decreases','Small test',
        'Test a small increase before changing every price. Cut a price only if extra sales can cover the lower margin.',
        'A 5% increase earns more per sale, but it can still lose money if enough customers leave. The table shows the sales loss each branch could absorb under a simple constant-mix calculation.',
        'Try one change with a comparison group. Track total basket profit, customer return and customers switching products.',
        [f'Uses the latest {rdays} calendar days. For +5%: maximum proportional volume loss = 1 − old gross profit / (old gross profit + 5% of revenue).',
         'Assumes unchanged product mix, discounts, unit costs and proportional volume loss. This is a break-even gate, not a measured customer response.',
         'A price decrease requires more units to sell. There is no evidence in this CSV that customers would buy those extra units.'],
        [dict(branch=r['branch'],increase=r['increase'],sales_loss_limit=r['sales_loss_limit'],price_cut_extra_sales=r['price_cut_extra_sales']) for r in price_rows],
        ['Branch','Increase to test','+5%: maximum volume loss','−5%: extra volume needed']))
    # Search actual pairs in branch/time windows, then check their occurrence in a later period.
    split=first+pd.Timedelta(days=max(1,int(days*.7)))
    pairs=[]
    for branch in branches.index:
        for start,end,label in [(7,11,'07:00–11:00'),(11,19,'11:00–19:00'),(19,24,'19:00–24:00')]:
            t=x[x.branch.eq(branch)&x.hour.between(start,end-1)]
            counts=[]
            for earlier in (True,False):
                section=t[t.date.lt(split) if earlier else t.date.ge(split)]
                co=Counter()
                from itertools import combinations
                for items in section.groupby('transaction')['product'].agg(lambda v:sorted(set(v))):
                    co.update(combinations(items,2))
                counts.append(co)
            for (a,c),n in counts[0].items():
                later=counts[1][a,c]
                if n<5 or later<3: continue
                ga=t[t['product'].eq(a)].sort_values('datetime');gb=t[t['product'].eq(c)].sort_values('datetime')
                price=float(ga.price.iloc[-1]+gb.price.iloc[-1])
                pairs.append(dict(branch=str(branch),items=f'{a} + {c}',when=label,
                    price=usd(price,2),earlier=int(n),later=int(later),score=min(n,later)))
    pairs.sort(key=lambda r:(r['score'],r['earlier']+r['later']),reverse=True)
    chosen=[];seen=set()
    for p in pairs:
        identity=(p['branch'],p['items'])
        if identity in seen:continue
        chosen.append(p);seen.add(identity)
        if len(chosen)==4:break
    if chosen:
        best=chosen[0]
        action=f"Try {best['items']} at {best['branch']} between {best['when']}—start with a full-price suggestion."
        reason=f"Customers bought this pair together {best['earlier']} times in the earlier period and {best['later']} times in the later period, in that branch and time window. That makes it a test candidate, not proof that a discount will sell more."
    else:
        action='Start a small full-price pairing test; there is no repeated pair with enough observations to rank here.'
        reason='The file has too few repeated two-item baskets across earlier and later dates to support a specific combo.'
    cards.append(card('combos','Combo offers: which items & when','Candidate to test',action,reason,
        'Offer the pair to some comparable customers and keep a no-offer group. Add a discount only if extra purchases cover discounts given to people who already buy both.',
        ['Candidates require at least 5 earlier and 3 later pair baskets in the same branch and time window.',
         'Ranking uses repeated co-purchase counts, so popular items can dominate. It is not a causal test or proof of special affinity.',
         'Prices shown add the latest observed menu price for each item in that branch/window; they are not an optimized offer price.',
         'The time window identifies where the pair was observed, not when a promotion would create the largest extra demand.'],
        [{k:p[k] for k in ('branch','items','when','price','earlier','later')} for p in chosen],
        ['Branch','Pair to test','Time','Full menu-price total','Earlier baskets','Later baskets']))
    by_key={c['key']:c for c in cards}
    by_key['hours']['highlights']=[f"{r['branch']}: {r['candidate']}. That hour currently contributes about {r['hourly_contribution']} per day." for r in hours]
    by_key['closure']['highlights']=[f"{weakest}: {usd(float(branches.loc[weakest,'gp'])/days,2)} gross profit per calendar day, before payroll and rent."]
    by_key['restock']['highlights']=[]
    for branch in branches.index:
        top=next((r for r in restock if r['branch']==branch),None)
        if top: by_key['restock']['highlights'].append(f"{branch}: {top['item']} sells about {top['daily_units']} units per day.")
    by_key['waste']['highlights']=[f"{r['branch']}: {r['item']} sells about {r['daily']:.1f} per day. Check batch size and actual leftovers." for r in slow[:3]]
    by_key['pricing']['highlights']=[f"{r['branch']}: a 5% increase can absorb up to {r['sales_loss_limit']} fewer sales; a 5% cut needs {r['price_cut_extra_sales']} more sales to break even." for r in price_rows]
    by_key['combos']['highlights']=[f"{p['branch']}, {p['when']}: {p['items']}. Latest observed full-price total: {p['price']}." for p in chosen[:2]]
    notes=[f'Uses {len(x):,} item lines across {len(b):,} orders from {first.date()} to {last.date()}.',
           'Gross profit subtracts recorded product costs; it does not subtract payroll, rent or waste.',
           'No actual operating costs, inventory counts, expiry logs or promotion-response measurements are assumed.',
           'Recommendations are review priorities and small tests, not guaranteed savings.']
    if days<28: notes.append('Less than four weeks of sales: treat timing and preparation patterns as tentative.')
    duplicates=int(x[list(RENAME.values())].duplicated().sum())
    if duplicates: notes.append(f'{duplicates:,} duplicate-looking rows were retained because they may be legitimate line items.')
    if ignored: notes.append('Extra columns were not used: '+', '.join(ignored)+'. Inventory, expiry and operating-cost data need a dedicated mapping before use.')
    report=dict(title='Your business recommendations',period=f'{first.date()} to {last.date()}',
        summary=dict(branches=len(branches),orders=len(b),revenue=usd(float(x.revenue.sum())),gross_profit=usd(float(x.gp.sum()))),
        cards=cards,notes=notes)
    from decision_room.charts import attach_charts
    return attach_charts(x,report)
