"""Analysis functions independent of the dashboard; monetary outputs are USD."""
from collections import Counter
from itertools import combinations, permutations
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RENAME = {'Transaction ID':'transaction', 'Date':'date', 'Time':'time', 'Branch':'branch',
          'Customer ID':'customer', 'Order Type':'order_type', 'Product':'product',
          'Category':'category', 'Quantity':'quantity', 'Unit Price (USD)':'price',
          'Discount Rate':'discount', 'Unit Cost (USD)':'cost',
          'Line Revenue (USD)':'revenue', 'Line Gross Profit (USD)':'gp'}

def load_data(path=ROOT / 'stories_transactions.csv'):
    """Validate schema, retain all original records and derive analytical features."""
    raw = pd.read_csv(path)
    if set(raw) != set(RENAME):
        raise ValueError(f'Expected columns: {list(RENAME)}')
    x = raw.rename(columns=RENAME).copy()
    if x.empty:
        raise ValueError('The transaction file is empty')
    for column in ['quantity','price','discount','cost','revenue','gp']:
        x[column]=pd.to_numeric(x[column],errors='raise')
    if not np.isfinite(x[['quantity','price','discount','cost','revenue','gp']]).all().all():
        raise ValueError('Financial fields must contain finite numbers')
    x['datetime'] = pd.to_datetime(x.date + ' ' + x.time, format='%Y-%m-%d %H:%M:%S')
    x['date'] = x.datetime.dt.normalize()
    x['month'] = x.datetime.dt.strftime('%Y-%m')
    x['week'] = x.datetime.dt.strftime('%G-W%V')
    x['weekday'] = x.datetime.dt.dayofweek
    x['hour'] = x.datetime.dt.hour
    x['weekend'] = x.weekday >= 5
    x['line_cost'] = x.quantity * x.cost
    x['list_value'] = x.quantity * x.price
    x['concession'] = x.list_value * x.discount
    x['unit_contribution'] = x.price * (1-x.discount)-x.cost
    x['margin'] = x.gp / x.revenue.replace(0, np.nan)
    x['discounted'] = x.discount > 0
    return x

def baskets(x):
    """Aggregate full baskets, never treating a line as an independent order."""
    return x.groupby('transaction').agg(date=('date','first'), month=('month','first'),
        weekday=('weekday','first'), hour=('hour','first'), branch=('branch','first'),
        order_type=('order_type','first'), customer=('customer','first'),
        revenue=('revenue','sum'), gp=('gp','sum'), units=('quantity','sum'),
        products=('product','nunique'), lines=('product','size'), discounted=('discounted','max'))

def validate(x, path=ROOT / 'stories_transactions.csv'):
    """Report half-cent financial exceptions without altering source amounts."""
    raw = pd.read_csv(path)
    revenue_error = (x.revenue-x.list_value*(1-x.discount)).abs()
    gp_error = (x.gp-(x.revenue-x.line_cost)).abs()
    required = x[list(RENAME.values())].drop(columns='customer')
    return dict(source_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        rows=len(x), columns=len(raw.columns), transactions=x.transaction.nunique(),
        products=x["product"].nunique(), customers=x.customer.nunique(),
        branches=sorted(x.branch.unique()), first_date=str(x.date.min().date()),
        last_date=str(x.date.max().date()), missing_by_column=raw.isna().sum().to_dict(),
        missing_customer_line_share=float(x.customer.isna().mean()),
        missing_customer_basket_share=float(baskets(x).customer.isna().mean()),
        missing_required=int(required.isna().sum().sum()),
        missing_calendar_days=len(pd.date_range(x.date.min(),x.date.max()).difference(x.date)),
        exact_duplicate_excess=int(raw.duplicated().sum()),
        duplicate_excess_revenue=float(x.loc[raw.duplicated(),'revenue'].sum()),
        revenue_exceptions_half_cent=int((revenue_error > .00500001).sum()),
        gp_exceptions_half_cent=int((gp_error > .00500001).sum()),
        maximum_revenue_error=float(revenue_error.max()), maximum_gp_error=float(gp_error.max()),
        nonpositive_quantity=int((x.quantity<=0).sum()),
        invalid_discount=int((~x.discount.between(0,1)).sum()),
        invalid_money=int((x[['price','cost','revenue']]<0).any(axis=1).sum()),
        nonfinite_financial_rows=int((~np.isfinite(x[['quantity','price','cost','revenue','gp','discount']])).any(axis=1).sum()),
        metadata_conflicts=int(x.fillna({'customer':'ANONYMOUS'}).groupby('transaction')[
            ['date','time','branch','customer','order_type']].nunique().gt(1).any(axis=1).sum()),
        discount_rates=sorted(x.discount.unique().tolist()),
        quantity_distribution=x.quantity.value_counts().sort_index().to_dict(),
        revenue=float(x.revenue.sum()), gp=float(x.gp.sum()))

def summary(x, by):
    t = x.groupby(by, observed=True).agg(revenue=('revenue','sum'), gp=('gp','sum'),
        transactions=('transaction','nunique'), units=('quantity','sum'))
    t['margin'] = t.gp/t.revenue.replace(0,np.nan)
    t['average_transaction_value'] = t.revenue/t.transactions
    t['gp_per_transaction'] = t.gp/t.transactions
    return t.reset_index()

def matched_products(x):
    """Same-product means and fixed-cost diagnostics; verify constancy before use."""
    grouped = x.groupby(['product','branch'])
    t = grouped.agg(price=('price','mean'), cost=('cost','mean'),
        price_values=('price','nunique'), cost_values=('cost','nunique')).unstack('branch')
    t.columns = ['_'.join(c) for c in t.columns]
    if not {'cost_Garden','cost_Harbour'}.issubset(t):
        return pd.DataFrame()
    t['cost_ratio'] = t.cost_Garden/t.cost_Harbour
    t['price_ratio'] = t.price_Garden/t.price_Harbour
    g = x[x.branch.eq('Garden')].copy()
    g['opportunity'] = g.quantity*(g.cost-g["product"].map(t.cost_Harbour))
    t['opportunity'] = g.groupby('product').opportunity.sum(min_count=1)
    t['garden_units'] = g.groupby('product').quantity.sum()
    return t.reset_index().sort_values('opportunity', ascending=False)

def counterfactual(x, reference, recovery=1., coverage=1., price_change=0., demand_loss=0., expense=0.):
    """Historical Garden replay; proportional coverage and volume loss, fixed mix.

    Reference costs must be supplied separately so branch filters cannot erase
    the comparison. Positive gap only; missing products are excluded and reported.
    """
    if not 0 <= recovery <= 1 or not 0 <= coverage <= 1 or not 0 <= demand_loss <= 1 or expense < 0 or price_change < -1:
        raise ValueError('Invalid scenario assumptions')
    g = x[x.branch.eq('Garden')].copy()
    costs = reference[reference.branch.eq('Harbour')].groupby('product').cost.mean()
    mapped = g["product"].map(costs)
    gap = (g.quantity*(g.cost-mapped).clip(lower=0)).sum()
    saved = gap*recovery*coverage
    baseline_revenue, baseline_gp = float(g.revenue.sum()), float(g.gp.sum())
    revenue = baseline_revenue*(1+price_change)*(1-demand_loss)
    gp_before_loss = baseline_gp + baseline_revenue*price_change + saved
    gp = gp_before_loss*(1-demand_loss)
    return dict(baseline_revenue=baseline_revenue, baseline_gp=baseline_gp,
        matched_gap=float(gap), unmatched_lines=int(mapped.isna().sum()),
        revenue=revenue, gp=gp, net_benefit=gp-baseline_gp-expense,
        break_even_demand_loss=(gp_before_loss-baseline_gp-expense)/gp_before_loss if gp_before_loss>0 else np.nan)

def decomposition(x):
    """Exact Shapley decomposition of GP/unit: mix, price, realized discount, cost.

    Average all 24 factor orderings to allocate interactions once. Common
    product universe is required. Discounts weighted by list value per product.
    """
    arrays = {}
    for branch in ['Garden','Harbour']:
        d = x[x.branch.eq(branch)]
        a = d.groupby('product').agg(q=('quantity','sum'), list=('list_value','sum'),
            concessions=('concession','sum'), cost=('line_cost','sum'))
        a['mix']=a.q/a.q.sum(); a['price']=a['list']/a.q
        a['discount']=a.concessions/a['list']; a['cost']=a.cost/a.q
        arrays[branch]=a[['mix','price','discount','cost']]
    if not arrays['Garden'].index.equals(arrays['Harbour'].index):
        raise ValueError('Decomposition requires identical product universe')
    factors=['mix','price','discount','cost']
    def value(a): return float((a.mix*(a.price*(1-a.discount)-a.cost)).sum())
    effects=Counter()
    for order in permutations(factors):
        a=arrays['Garden'].copy(); previous=value(a)
        for factor in order:
            a[factor]=arrays['Harbour'][factor]; new=value(a)
            effects[factor]+=(new-previous)/24; previous=new
    recorded=x.groupby('branch').apply(lambda d:d.gp.sum()/d.quantity.sum())
    effects['source_rounding']=float(recorded['Harbour']-recorded['Garden']-sum(effects.values()))
    return pd.DataFrame([{'factor':k,'harbour_minus_garden_gp_per_unit':v} for k,v in effects.items()])

def associations(x, min_count=30):
    """Train January–April; validate same pairs May–June; presence per basket."""
    def counts(d):
        groups=d.groupby('transaction')["product"].agg(lambda s: sorted(set(s)))
        singles=Counter(p for g in groups for p in g)
        pairs=Counter(pair for g in groups for pair in combinations(g,2))
        return len(groups),singles,pairs
    n,a,p=counts(x[x.date < '2026-05-01'])
    m,b,q=counts(x[x.date >= '2026-05-01'])
    rows=[]
    for (u,v),count in p.items():
        if count<min_count: continue
        rows.append(dict(product_a=u,product_b=v,train_count=count,train_support=count/n,
            train_confidence=count/a[u],train_lift=count*n/(a[u]*a[v]),
            test_count=q[u,v],test_support=q[u,v]/m if m else np.nan,
            test_confidence=q[u,v]/b[u] if b[u] else np.nan,
            test_lift=q[u,v]*m/(b[u]*b[v]) if b[u]*b[v] else np.nan))
    return pd.DataFrame(rows,columns=['product_a','product_b','train_count','train_support',
        'train_confidence','train_lift','test_count','test_support','test_confidence','test_lift']).sort_values('train_lift',ascending=False)

def bundle_scenarios(x, pairs):
    """Illustrative cross-sell to A-only baskets; discount leaks to existing pairs."""
    rows=[]
    for _,pair in pairs.head(10).iterrows():
        a,b=pair.product_a,pair.product_b
        a_ids=set(x.loc[x["product"].eq(a),'transaction']); b_ids=set(x.loc[x["product"].eq(b),'transaction'])
        eligible=len(a_ids-b_ids); existing=len(a_ids&b_ids)
        lines=x[x["product"].eq(b)]
        price=lines.list_value.sum()/lines.quantity.sum()
        contribution=lines.gp.sum()/lines.quantity.sum()
        for adoption in [.02,.05,.10]:
            rebate=.10*price
            gain=eligible*adoption*(contribution-rebate)-existing*rebate
            rows.append(dict(product_a=a,product_b=b,eligible_baskets=eligible,existing_pairs=existing,
                assumed_adoption=adoption,assumed_discount=.10,incremental_gp=gain,
                attached_unit_gp=contribution,break_even_discount=contribution/price,
                break_even_adoption=existing*rebate/(eligible*(contribution-rebate)) if eligible and contribution>rebate else np.nan))
    return pd.DataFrame(rows)
