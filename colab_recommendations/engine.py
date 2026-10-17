"""Deterministic, local-only Stories decision arithmetic. No network or raw-data exports."""
from collections import Counter
from itertools import combinations
import hashlib
import json
import numpy as np
import pandas as pd

COLUMNS = {'Transaction ID':'transaction','Date':'date','Time':'time','Branch':'branch',
 'Customer ID':'customer','Order Type':'order_type','Product':'product','Category':'category',
 'Quantity':'quantity','Unit Price (USD)':'price','Discount Rate':'discount',
 'Unit Cost (USD)':'cost','Line Revenue (USD)':'revenue','Line Gross Profit (USD)':'gp'}
NUMERIC = ['quantity','price','discount','cost','revenue','gp']
LAYERS = ['Opening hours', 'Permanent closure', 'Restock / preparation', 'Expiry markdown',
          'Loyalty', 'Price increase', 'Item discount', 'Two-item combo', 'Delivery offer']

def load_transactions(source, drop_duplicates=False):
    raw = pd.read_csv(source, dtype={'Transaction ID':'string','Customer ID':'string'})
    missing = set(COLUMNS)-set(raw)
    if missing:
        raise ValueError('Missing columns: '+', '.join(sorted(missing)))
    raw = raw[list(COLUMNS)]
    if raw.empty:
        raise ValueError('No transaction rows.')
    duplicates = raw.duplicated()
    quality = {'source_rows':len(raw), 'exact_duplicate_excess':int(duplicates.sum()),
               'duplicate_revenue':float(pd.to_numeric(raw.loc[duplicates,'Line Revenue (USD)']).sum()),
               'duplicate_policy':'remove exact repeated rows' if drop_duplicates else 'retain source rows'}
    if drop_duplicates:
        raw = raw.loc[~duplicates].copy()
    x = raw.rename(columns=COLUMNS).copy()
    required = list(set(COLUMNS.values())-{'customer'})
    if x[required].isna().any().any():
        raise ValueError('Missing required fields; only Customer ID may be blank.')
    for c in NUMERIC:
        x[c] = pd.to_numeric(x[c], errors='raise')
    if not np.isfinite(x[NUMERIC].to_numpy()).all():
        raise ValueError('Nonfinite financial values.')
    if (x.quantity<=0).any() or (x.quantity%1!=0).any() or not x.discount.between(0,1).all() or (x[['price','cost','revenue']]<0).any().any():
        raise ValueError('Require positive integer quantities, nonnegative money, discounts in [0,1].')
    x['datetime'] = pd.to_datetime(x.date.astype(str)+' '+x.time.astype(str), format='%Y-%m-%d %H:%M:%S', errors='raise')
    x['date'] = x.datetime.dt.normalize()
    x['hour'] = x.datetime.dt.hour
    x['weekday'] = x.datetime.dt.dayofweek
    x['customer'] = x.customer.replace(r'^\s*$',pd.NA,regex=True)
    conflicts = x.assign(customer=x.customer.fillna('__anonymous__')).groupby('transaction')[['date','time','branch','customer','order_type']].nunique().gt(1).any(axis=1)
    if conflicts.any():
        raise ValueError('Conflicting basket metadata; repair transaction IDs before analysis.')
    x['list_value'] = x.quantity*x.price
    x['line_cost'] = x.quantity*x.cost
    x['discounted'] = x.discount>0
    quality.update({'rows_used':len(x),'baskets':x.transaction.nunique(),
      'first_date':str(x.date.min().date()),'last_date':str(x.date.max().date()),
      'missing_customer_basket_share':float(baskets(x).customer.isna().mean()),
      'revenue_exceptions_over_half_cent':int(((x.revenue-x.list_value*(1-x.discount)).abs()>.005001).sum()),
      'gp_exceptions_over_half_cent':int(((x.gp-(x.revenue-x.line_cost)).abs()>.005001).sum()),
      'absent_calendar_days':len(pd.date_range(x.date.min(),x.date.max()).difference(x.date.unique())),
      'order_types':sorted(x.order_type.unique().tolist())})
    return x, quality

def baskets(x):
    return x.groupby('transaction',sort=False).agg(date=('date','first'),branch=('branch','first'),
      hour=('hour','first'),customer=('customer','first'),order_type=('order_type','first'),
      revenue=('revenue','sum'),gp=('gp','sum'),units=('quantity','sum'))

def calendar_days(x):
    return max(1,(x.date.max()-x.date.min()).days+1)

def scope(x, branch, lookback=56):
    end = x.date.max()
    start = max(x.date.min(),end-pd.Timedelta(days=lookback-1))
    selected=x.loc[x.branch.eq(branch)&x.date.between(start,end)].copy()
    selected.attrs.update(calendar_start=start,calendar_end=end)
    return selected, (end-start).days+1

def product_stats(x, product):
    t = x[x['product'].eq(product)]
    if t.empty:
        raise ValueError('Product absent from branch/window.')
    q=t.quantity.sum()
    return {'units':float(q),'price':float(t.list_value.sum()/q),
            'net_price':float(t.revenue.sum()/q),'cost':float(t.line_cost.sum()/q),
            'margin':float(t.gp.sum()/q),'basket_ids':t.transaction.unique()}

def safe_ratio(a,b):
    return float(a/b) if b>0 else np.nan

def defaults(x):
    branches=sorted(x.branch.unique())
    products=x[x.branch.eq(branches[0])].groupby('product').quantity.sum().sort_values(ascending=False).index.tolist()
    return dict(branch=branches[0],destination=branches[-1],product=products[0],second=products[1],
      horizon=30,lookback=56,start_hour=14,end_hour=18,
      new_open=8,new_close=23,avoidable_hour_cost=0.,recapture=.0,recapture_margin=1.,
      extension_orders_hour=0.,extension_gp_order=0.,extension_hour_cost=0.,hours_setup=0.,
      fixed_monthly=0.,fixed_avoidable=.0,other_saved_daily=0.,exit_cost=0.,migration=.0,
      destination_capacity_daily=0.,destination_displacement=.0,transfer_cost_order=0.,
      on_hand=0.,current_order=float(np.ceil(x[x.branch.eq(branches[0]) & x['product'].eq(products[0])].quantity.sum()/calendar_days(x))),lead_days=1,service_quantile=.80,salvage=0.,disposal=0.,
      shortage_penalty=0.,restock_setup=0.,expiry_units_daily=0.,expiry_base_sell=.0,
      expiry_offer_sell=.0,expiry_discount=.20,expiry_cannibal_daily=0.,handling=0.,waste_setup=0.,
      loyalty_reach=.25,loyalty_extra_visits=0.,loyalty_reward=0.,loyalty_base_visits=1.,
      loyalty_displacement=.0,loyalty_setup=0.,price_increase=.05,item_loss=.0,
      basket_loss=.0,substitution_share=.0,alternative_margin=0.,price_setup=0.,
      item_discount=.10,discount_incremental_units_daily=0.,discount_substitution=.0,
      discount_alternative_margin=0.,discount_lost_baskets_daily=0.,discount_setup=0.,
      combo_discount=.10,combo_conversion=.0,combo_substitution=.0,combo_alternative_margin=0.,
      combo_lost_baskets_daily=0.,combo_cost=0.,delivery_orders_daily=0.,delivery_incremental=.0,
      delivery_fee=0.,delivery_commission=.25,delivery_packaging=0.,delivery_courier=0.,
      delivery_discount=.10,delivery_displaced_gp=0.,delivery_lost_baskets_daily=0.,delivery_setup=0.)

def _validate(p):
    fractions=['recapture','fixed_avoidable','migration','destination_displacement','service_quantile',
     'expiry_base_sell','expiry_offer_sell','expiry_discount','loyalty_reach','loyalty_displacement',
     'item_loss','basket_loss','substitution_share','item_discount','discount_substitution',
     'combo_discount','combo_conversion','combo_substitution','delivery_incremental','delivery_commission','delivery_discount']
    for k in fractions:
        if not 0<=p[k]<=1: raise ValueError(k+' must be in [0,1]')
    if any(p[k]!=int(p[k]) for k in ['horizon','lookback','lead_days','start_hour','end_hour','new_open','new_close']):
        raise ValueError('Days and hours must be whole integers.')
    if p['horizon']<1 or p['lookback']<1 or p['lead_days']<1:
        raise ValueError('Horizon, lookback and lead days must be positive.')
    if not 0<=p['new_open']<p['new_close']<=24 or not 0<=p['start_hour']<p['end_hour']<=24:
        raise ValueError('Hours must define a nonempty same-day interval, end exclusive.')
    for k,v in p.items():
        if isinstance(v,(int,float)) and (not np.isfinite(v) or v<0):
            raise ValueError(k+' must be finite and nonnegative.')

def daily_series(x,product):
    idx=pd.date_range(x.attrs.get('calendar_start',x.date.min()),x.attrs.get('calendar_end',x.date.max()))
    return x[x['product'].eq(product)].groupby('date').quantity.sum().reindex(idx,fill_value=0).astype(float)

def predict(history, date, model):
    h=history.tail(56)
    if model=='weekday':
        same=h[h.index.dayofweek==date.dayofweek]
        if len(same): return float(same.mean())
    return float(h.tail(28).mean()) if len(h) else 0.

def forecast_backtest(series):
    """Choose on penultimate 14 dates, report untouched final 14; rolling one-step origins."""
    n=len(series)
    if n<42:
        return pd.DataFrame(),pd.DataFrame(), 'mean28'
    val_start=max(14,n-28); test_start=n-14
    records=[]
    for i in range(val_start,n):
        hist=series.iloc[:i]
        for model in ['mean28','weekday']:
            records.append(dict(date=series.index[i],split='validation' if i<test_start else 'test',
              model=model,actual=float(series.iloc[i]),prediction=predict(hist,series.index[i],model)))
    details=pd.DataFrame(records)
    details['absolute_error']=(details.actual-details.prediction).abs()
    scores=details.groupby(['split','model']).agg(MAE=('absolute_error','mean'),
      total_error=('absolute_error','sum'),total_actual=('actual','sum')).reset_index()
    scores['WAPE']=scores.total_error/scores.total_actual.replace(0,np.nan)
    winner=scores[scores.split.eq('validation')].sort_values(['MAE','model']).iloc[0].model
    return details,scores,winner

def restock_policy(series,s,p):
    _,scores,winner=forecast_backtest(series)
    rng=np.random.default_rng(490)
    samples=series.tail(56).to_numpy()
    # Sales proxy draws: lead-period totals; dependence and censoring are explicit limitations.
    draws=rng.choice(samples,size=(4000,int(p['lead_days'])),replace=True).sum(axis=1)
    target=float(np.ceil(np.quantile(draws,p['service_quantile'])))
    order=max(0.,target-p['on_hand'])
    def contribution(order_qty):
        stock=p['on_hand']+order_qty
        sold=np.minimum(draws,stock);left=np.maximum(stock-draws,0)
        return sold*s['net_price']-order_qty*s['cost']+left*(p['salvage']-p['disposal'])-np.maximum(draws-stock,0)*p['shortage_penalty']
    # Each draw is a nonoverlapping replenishment cycle, with starting inventory reset by assumption.
    cycles=p['horizon']/p['lead_days']
    delta=float((contribution(order)-contribution(p['current_order'])).mean()*cycles-p['restock_setup'])
    costs=s['cost']-p['salvage']+p['disposal']
    under=s['net_price']-s['cost']+p['shortage_penalty']
    critical=safe_ratio(max(0,under),max(0,under)+max(0,costs))
    future=pd.date_range(series.index.max()+pd.Timedelta(days=1),periods=7)
    forecast=pd.DataFrame({'date':future,'predicted_units':[predict(series,d,winner) for d in future]})
    return dict(delta=delta,target=target,order=order,critical_quantile=critical,
      expected_leftovers=float(np.maximum(p['on_hand']+order-draws,0).mean()),
      proxy_stockout_probability=float((draws>p['on_hand']+order).mean()),scores=scores,forecast=forecast,
      chosen_model=winner,lead_sales_p10=float(np.quantile(draws,.1)),lead_sales_p90=float(np.quantile(draws,.9)))

def pair_evidence(x,min_count=5):
    """Temporal pair discovery; basket presence avoids quantity/duplicate inflation."""
    cut=x.date.min()+pd.Timedelta(days=int(calendar_days(x)*.70))
    def count(t):
        groups=t.groupby('transaction')['product'].agg(lambda s:sorted(set(s)))
        singles=Counter(a for g in groups for a in g)
        pairs=Counter(p for g in groups for p in combinations(g,2))
        return len(groups),singles,pairs
    n,a,b=count(x[x.date<cut]);m,c,d=count(x[x.date>=cut])
    out=[]
    for (u,v),k in b.items():
        if k<min_count: continue
        out.append(dict(product_a=u,product_b=v,train_pair_baskets=k,train_support=safe_ratio(k,n),
          train_lift=safe_ratio(k*n,a[u]*a[v]),holdout_pair_baskets=d[u,v],
          holdout_support=safe_ratio(d[u,v],m),holdout_lift=safe_ratio(d[u,v]*m,c[u]*c[v]),
          split_date=str(cut.date())))
    if not out: return pd.DataFrame(columns=['product_a','product_b','train_pair_baskets','train_lift','holdout_pair_baskets','holdout_lift'])
    return pd.DataFrame(out).sort_values(['train_pair_baskets','product_a','product_b'],ascending=[False,True,True])

def loyalty_evidence(x):
    """30-day recognized return, right-censored first visits excluded; anonymous not imputed."""
    b=baskets(x);known=b.dropna(subset=['customer'])
    if known.empty:return dict(identified_customers=0,mature_customers=0,recognized_return30=np.nan)
    dates=known.groupby('customer').date.agg(lambda d:sorted(set(d)))
    mature=dates[dates.map(lambda d:d[0]<=x.date.max()-pd.Timedelta(days=30))]
    returned=mature.map(lambda d:any(0<(v-d[0]).days<=30 for v in d[1:]))
    return dict(identified_customers=len(dates),mature_customers=len(mature),
      recognized_return30=float(returned.mean()) if len(mature) else np.nan)

def evaluate(x, assumptions):
    p=defaults(x);p.update(assumptions);_validate(p)
    t,days=scope(x,p['branch'],int(p['lookback']))
    if t.empty:raise ValueError('No rows in branch/window.')
    b=baskets(t);scale=p['horizon']/days
    s=product_stats(t,p['product'])
    h=t[t.hour.between(p['start_hour'],p['end_hour']-1)]
    hb=baskets(h)
    q=s['units']*scale; full_gp=float(b.gp.sum()*scale)
    avg_gp=float(b.gp.mean());avg_revenue=float(b.revenue.mean());avg_cost=avg_revenue-avg_gp
    rows=[]; gates=[]
    def add(layer,delta,gate,detail,formula):
        rows.append(dict(scenario=layer,delta_usd=float(delta),horizon_days=p['horizon'],
          evidence='Conditional scenario; response/cost inputs assumed',gate=gate,detail=detail,formula=formula))
    rows.append(dict(scenario='Do nothing',delta_usd=0.,horizon_days=p['horizon'],
      evidence='Reference: historical rate replay, not a forecast',gate='Baseline',
      detail=f'Recorded branch GP replay ${full_gp:,.2f}; unmeasured operating costs excluded.',formula='Δ = 0'))
    # Operating hours: source support is observed selling hours, not a documented roster.
    observed_open=int(t.hour.min());observed_close=int(t.hour.max()+1)
    removed=b[(b.hour<p['new_open'])|(b.hour>=p['new_close'])]
    removed_hours=len([i for i in range(observed_open,observed_close) if i<p['new_open'] or i>=p['new_close']])
    added_hours=max(0,observed_open-p['new_open'])+max(0,p['new_close']-observed_close)
    lost=float(removed.gp.sum()*scale)
    hourly_days=removed_hours*p['horizon']
    saved=hourly_days*p['avoidable_hour_cost']
    regained=lost*p['recapture']*p['recapture_margin']
    extension=added_hours*p['horizon']*(p['extension_orders_hour']*p['extension_gp_order']-p['extension_hour_cost'])
    hours_delta=saved-lost+regained+extension-p['hours_setup']
    gate=safe_ratio(lost-regained-extension+p['hours_setup'],hourly_days)
    add('Opening hours',hours_delta,f'Break-even avoidable $/removed hour-day: {gate:.2f}',
      f'Observed selling support {observed_open}:00–{observed_close}:00. Removed GP ${lost:.2f}; assumed recapture ${regained:.2f}; extension net ${extension:.2f}.',
      'Δ = avoidable hourly savings − removed basket GP + recaptured GP + extension net − setup')
    # Permanent closure: destinations are independent of branch filter.
    dest,_=scope(x,p['destination'],int(p['lookback']))
    db=baskets(dest);dest_gp=float(db.gp.mean()) if len(db) else 0.
    if p['destination']==p['branch']:
        dest_gp=0.;capacity=0.
    else:capacity=p['destination_capacity_daily']*p['horizon']
    src_orders=len(b)*scale
    migrants=min(src_orders*p['migration'],capacity)
    per_migrant=dest_gp*(1-p['destination_displacement'])-p['transfer_cost_order']
    fixed=p['fixed_monthly']*p['fixed_avoidable']*p['horizon']/30+p['other_saved_daily']*p['horizon']
    recurring=fixed-full_gp+migrants*per_migrant
    closure=recurring-p['exit_cost']
    need=safe_ratio(full_gp+p['exit_cost']-fixed,src_orders*per_migrant)
    max_migration=safe_ratio(min(src_orders,capacity),src_orders)
    add('Permanent closure',closure,f'Break-even migration fraction {need:.1%}; capacity ceiling {max_migration:.1%}',
      f'Full one-time exit ${p["exit_cost"]:.2f}; assumed avoidable fixed ${fixed:.2f}; migrated orders {migrants:.1f}. Recurring horizon Δ ${recurring:.2f}.',
      'Δ = avoidable fixed + other saved cash − source GP + capacity-capped migration × (destination GP × (1−displacement)−transfer cost) − exit')
    gates.append(dict(scenario='Permanent closure',metric='exit_payback_months_if_recurring_positive',value=safe_ratio(p['exit_cost'],recurring/p['horizon']*30)))
    restock=restock_policy(daily_series(t,p['product']),s,p)
    add('Restock / preparation',restock['delta'],f'Proxy target {restock["target"]:.0f} units; order {restock["order"]:.0f}; economic quantile {restock["critical_quantile"]:.1%}',
      f'Compared with assumed current order {p["current_order"]:.0f}/cycle; starting stock resets each {p["lead_days"]}-day cycle. Sales may be censored demand.',
      'Δ = cycles × E[policy contribution − current-order contribution] − setup; contribution = sold × net price − ordered × cost + leftover × (salvage−disposal) − shortage penalty')
    # Expiry: acquisition cost sunk for stock already held; leakage is paid on organic sales too.
    n=p['expiry_units_daily']*p['horizon'];residual=p['salvage']-p['disposal']
    base_unit=p['expiry_base_sell']*s['price']+(1-p['expiry_base_sell'])*residual
    offer_unit=p['expiry_offer_sell']*(s['price']*(1-p['expiry_discount'])-p['handling'])+(1-p['expiry_offer_sell'])*residual
    cannibal=p['expiry_cannibal_daily']*p['horizon']*s['margin']
    waste=n*(offer_unit-base_unit)-cannibal-p['waste_setup']
    expiry_gate=safe_ratio(base_unit+safe_ratio(cannibal+p['waste_setup'],n)-residual,s['price']*(1-p['expiry_discount'])-p['handling']-residual)
    add('Expiry markdown',waste,f'Break-even offered sell-through {expiry_gate:.1%}',
      f'Assumed expiring units {n:.1f}; discount leakage on baseline sales ${n*p["expiry_base_sell"]*s["price"]*p["expiry_discount"]:.2f}; acquisition cost is sunk.',
      'Δ = expiry units × [offer expected recovery − baseline expected recovery] − regular-demand cannibalization GP − setup')
    # Loyalty: identified eligible people only; observed visits are not campaign effects.
    eligible=b.customer.nunique()*p['loyalty_reach']
    extra=eligible*p['loyalty_extra_visits']
    incremental_margin=avg_gp*(1-p['loyalty_displacement'])-p['loyalty_reward']
    loyalty_leak=eligible*p['loyalty_base_visits']*p['loyalty_reward']
    loyalty=extra*incremental_margin-loyalty_leak-p['loyalty_setup']
    visit_gate=safe_ratio(loyalty_leak+p['loyalty_setup'],eligible*incremental_margin)
    add('Loyalty',loyalty,f'Break-even extra visits/reached customer over horizon {visit_gate:.3f}',
      f'Observed identified customers {b.customer.nunique()}; assumed reached {eligible:.1f}; organic-visit reward leakage ${loyalty_leak:.2f}.',
      'Δ = reached × extra visits × [GP/visit × (1−displacement)−reward] − rewards on organic visits − setup')
    # Whole-basket loss first, then item attrition among surviving baskets; alternatives incremental vs item removed.
    containing=b.loc[b.index.isin(s['basket_ids'])]
    basket_gp=float(containing.gp.sum()*scale)
    uplift=q*s['net_price']*p['price_increase']
    target_gp=q*s['margin']
    alternative=q*p['item_loss']*p['substitution_share']*p['alternative_margin']
    retained_uplift=uplift*(1-p['item_loss'])
    inner=retained_uplift-target_gp*p['item_loss']+alternative
    price_delta=(1-p['basket_loss'])*inner-p['basket_loss']*basket_gp-p['price_setup']
    basket_gate=safe_ratio(inner-p['price_setup'],inner+basket_gp)
    add('Price increase',price_delta,f'Whole-basket loss break-even {basket_gate:.1%}; item-only at zero substitution {safe_ratio(uplift,uplift+target_gp):.1%}',
      f'Target GP ${target_gp:.2f}; containing-basket GP ${basket_gp:.2f}; no-loss price uplift ${uplift:.2f}.',
      'Δ = (1−basket loss) × [uplift × (1−item loss) − target GP × item loss + substitute GP] − basket loss × containing-basket GP − setup')
    # Item discount replaces current realized concessions: no stacking by assumption.
    discount_scope=h[h['product'].eq(p['product'])]
    discount_q=float(discount_scope.quantity.sum())*scale
    discount_net=safe_ratio(float(discount_scope.revenue.sum()),float(discount_scope.quantity.sum())) if len(discount_scope) else s['net_price']
    offer_price=s['price']*(1-p['item_discount'])
    discount_margin=offer_price-s['cost']
    leakage=discount_q*(discount_net-offer_price)
    inc=p['discount_incremental_units_daily']*p['horizon']
    unit_net=discount_margin-p['discount_substitution']*p['discount_alternative_margin']
    lost_b=p['discount_lost_baskets_daily']*p['horizon']*avg_gp
    discount=inc*unit_net-leakage-lost_b-p['discount_setup']
    discount_gate=safe_ratio(leakage+lost_b+p['discount_setup'],unit_net*p['horizon'])
    add('Item discount',discount,f'Break-even additional units/day {discount_gate:.2f}',
      f'Offer ${offer_price:.2f} replaces window average net ${discount_net:.2f}; existing-volume leakage ${leakage:.2f}; offer margin ${discount_margin:.2f}.',
      'Δ = extra units × (offer margin−substitution share × alternative GP) − current-volume leakage − lost whole-basket GP − setup')
    # Combo is one A + one B, attached to A-only baskets. Existing AB baskets receive same offer.
    if p['product']==p['second']: raise ValueError('Combo requires two different products.')
    a=product_stats(t,p['product']);z=product_stats(t,p['second'])
    aset=set(h.loc[h['product'].eq(p['product']),'transaction']);bset=set(h.loc[h['product'].eq(p['second']),'transaction'])
    both=aset&bset;only=aset-bset
    list_pair=a['price']+z['price'];combo_price=list_pair*(1-p['combo_discount'])
    # Measure actual pair revenue for one unit of each in co-purchase baskets (weighted per-basket prices).
    rev_existing=0.
    for _,g in h[h.transaction.isin(both)].groupby('transaction'):
        for prod in [p['product'],p['second']]:
            v=g[g['product'].eq(prod)];rev_existing+=float(v.revenue.sum()/v.quantity.sum())
    combo_leak=(rev_existing-len(both)*combo_price)*scale
    eligible=len(only)*scale;converted=eligible*p['combo_conversion']
    # New attachment gets the bundle price instead of former A revenue; includes rebate on A.
    former_a=h[h.transaction.isin(only)&h['product'].eq(p['product'])].groupby('transaction').agg(revenue=('revenue','sum'),quantity=('quantity','sum'))
    former_a_net=float((former_a.revenue/former_a.quantity).mean()) if len(former_a) else a['net_price']
    add_margin=combo_price-former_a_net-z['cost']-p['combo_substitution']*p['combo_alternative_margin']
    combo_lost=p['combo_lost_baskets_daily']*p['horizon']*(float(hb.gp.mean()) if len(hb) else avg_gp)
    combo=converted*add_margin-combo_leak-combo_lost-p['combo_cost']
    combo_gate=safe_ratio(combo_leak+combo_lost+p['combo_cost'],eligible*add_margin)
    add('Two-item combo',combo,f'Break-even A-only adoption {combo_gate:.1%}',
      f'{p["product"]} + {p["second"]}, {p["start_hour"]}:00–{p["end_hour"]}:00; list ${list_pair:.2f}, offer ${combo_price:.2f}; eligible {eligible:.1f}, existing pairs {len(both)*scale:.1f}; leakage ${combo_leak:.2f}.',
      'Δ = A-only baskets × adoption × (combo price−former A revenue−B cost−substitution GP) − existing-pair leakage − lost-basket GP − program cost')
    # Delivery conversion, channel migration and displacement are explicitly assumed.
    window_revenue=float(hb.revenue.mean()) if len(hb) else avg_revenue
    window_gp=float(hb.gp.mean()) if len(hb) else avg_gp
    window_cost=window_revenue-window_gp
    charged=window_revenue*(1-p['delivery_discount'])
    delivery_margin=charged*(1-p['delivery_commission'])+p['delivery_fee']-window_cost-p['delivery_packaging']-p['delivery_courier']
    orders=p['delivery_orders_daily']*p['horizon']
    old_gp=p['delivery_displaced_gp']
    net_per=delivery_margin-(1-p['delivery_incremental'])*old_gp
    lost=p['delivery_lost_baskets_daily']*p['horizon']*avg_gp
    delivery=orders*net_per-lost-p['delivery_setup']
    inc_gate=1-safe_ratio(delivery_margin-safe_ratio(lost+p['delivery_setup'],orders),old_gp)
    add('Delivery offer',delivery,f'Break-even genuinely incremental share {inc_gate:.1%}',
      f'NO delivery measurement inferred. In-store mix proxy: net delivery margin ${delivery_margin:.2f}/order; {orders:.1f} assumed orders at {p["start_hour"]}:00–{p["end_hour"]}:00.',
      'Δ = delivery orders × [delivery margin−(1−incremental share)×displaced in-store GP] − peak lost-basket GP − setup; margin = discounted basket × (1−commission)+retained fee−COGS−packaging−courier')
    ranking=pd.DataFrame(rows).sort_values('delta_usd',ascending=False,kind='stable').reset_index(drop=True)
    ranking['decision']=np.where(ranking.scenario.eq('Do nothing'),'Reference',np.where(ranking.delta_usd>0,'Candidate for controlled test','Fails these assumptions'))
    return dict(ranking=ranking,parameters=p,baseline_gp=full_gp,days=days,
      restock=restock,pairs=pair_evidence(t),loyalty=loyalty_evidence(t),gates=pd.DataFrame(gates),
      measured=dict(branch=p['branch'],days=days,rows=len(t),baskets=len(b),revenue=float(t.revenue.sum()),gp=float(t.gp.sum()),
        target_units=s['units'],target_price=s['price'],target_cost=s['cost'],customer_id_coverage=float(b.customer.notna().mean())),
      diagnostics=dict(combo_price=combo_price,combo_leakage=combo_leak,combo_eligible=eligible,combo_incremental_margin=add_margin,
        price_basket_exposure=basket_gp,price_uplift=uplift,delivery_margin=delivery_margin,
        closure_capacity_fraction=max_migration,closure_break_even_migration=need))

def sensitivity(x,p,key,values,layer):
    rows=[]
    for v in values:
        trial=dict(p);trial[key]=float(v)
        result=evaluate(x,trial)['ranking'].set_index('scenario').loc[layer]
        rows.append({key:float(v),'delta_usd':float(result.delta_usd)})
    return pd.DataFrame(rows)

def aggregate_report(result,quality):
    """Only aggregates and assumptions: never transaction/customer rows or identifiers."""
    p=result['parameters']
    lines=['# Stories Coffee — conditional decision report','',
      f'Branch: {p["branch"]}; calibration: last {result["days"]} calendar days; horizon: {p["horizon"]} days.',
      'USD throughout. Recorded gross profit is not net cash profit. No interventions are combined.',
      'Historical sales rates are replayed; campaign response and avoidable cash costs are assumptions.',
      'Positive scenarios qualify for a controlled pilot, not automatic rollout.','',
      '## Data checks','',json.dumps(quality,indent=2,default=str),'','## Scenario comparisons','']
    for r in result['ranking'].to_dict('records'):
        lines.extend([f'### {r["scenario"]}: Δ ${r["delta_usd"]:,.2f}',r['decision'],r['detail'],r['gate'],r['formula'],''])
    lines+=['## Assumptions',json.dumps(p,indent=2,default=str),'',
      '## Missing evidence and pilot gates',
      'Inventory/on-hand, waste/expiry, demand censoring, staffing, avoidable rent/payroll, exit contracts, elasticity, campaign assignment, delivery mix/cost and loyalty counterfactuals are not in the CSV.',
      'Randomize eligibility before purchase; include nonbuyers, whole-basket and chain contribution, substitution, future visits, service delays, complaints and inventory losses. Cluster inference at assignment level. Pre-specify duration, power, spending cap and operational stop rules.',
      'Forecast holdout accuracy validates sales prediction only. Co-purchase and recognized returns are descriptive; neither estimates treatment effects.',
      'Upload only authorized data. Colab and downloaded reports are subject to your access controls. Clear outputs before sharing the notebook.']
    return '\n\n'.join(lines)

def combo_candidates(x,p,top_per_window=3):
    """Discover on first 70%, check holdout; rank economic screens using assumed adoption.

    Window and SKU search is exploratory. Holdout support is descriptive stability,
    not independent causal validation or correction for searching many candidates.
    """
    out=[]
    for branch in sorted(x.branch.unique()):
        t,days=scope(x,branch,int(p['lookback']))
        for label,start,end in [('Morning',7,11),('Lunch',11,15),('Afternoon',15,19),('Evening',19,24)]:
            w=t[t.hour.between(start,end-1)]
            if w.empty:continue
            evidence=pair_evidence(w)
            if evidence.empty:continue
            for r in evidence.head(top_per_window).to_dict('records'):
                u,v=r['product_a'],r['product_b']
                a=product_stats(w,u);z=product_stats(w,v)
                aa=set(a['basket_ids']);zz=set(z['basket_ids']);both=aa&zz
                # Orient toward the larger A-only eligible pool, never on test profit.
                if len(zz-aa)>len(aa-zz):
                    u,v=v,u;a,z=z,a;aa,zz=zz,aa
                offer=(a['price']+z['price'])*(1-p['combo_discount'])
                leak=0.
                for _,g in w[w.transaction.isin(both)].groupby('transaction'):
                    former=0.
                    for prod in [u,v]:
                        f=g[g['product'].eq(prod)];former+=float(f.revenue.sum()/f.quantity.sum())
                    leak+=former-offer
                eligible=len(aa-zz)
                former=w[w.transaction.isin(aa-zz)&w['product'].eq(u)].groupby('transaction').agg(revenue=('revenue','sum'),quantity=('quantity','sum'))
                former_net=float((former.revenue/former.quantity).mean()) if len(former) else a['net_price']
                unit=offer-former_net-z['cost']-p['combo_substitution']*p['combo_alternative_margin']
                scale=p['horizon']/days
                gain=(eligible*p['combo_conversion']*unit-leak)*scale-p['combo_cost']
                out.append(dict(branch=branch,window=f'{label} {start}–{end}',product_a=u,product_b=v,
                  train_pairs=r['train_pair_baskets'],holdout_pairs=r['holdout_pair_baskets'],
                  train_lift=r['train_lift'],holdout_lift=r['holdout_lift'],
                  combo_price=offer,discount=p['combo_discount'],eligible_per_horizon=eligible*scale,
                  existing_pair_leakage=leak*scale,incremental_attachment_margin=unit,
                  break_even_adoption=safe_ratio(leak*scale+p['combo_cost'],eligible*scale*unit),
                  conditional_delta_before_queue_losses=gain,
                  why='Train-supported co-purchase; check holdout stability, then test A-only attachment.'))
    return pd.DataFrame(out).sort_values('conditional_delta_before_queue_losses',ascending=False) if out else pd.DataFrame()

def hourly_opportunities(x,p):
    """Rank delivery timing by observed in-store mix proxy; demand response still assumed."""
    t,days=scope(x,p['branch'],int(p['lookback']));b=baskets(t)
    rows=[]
    for hour in range(24):
        h=b[b.hour.eq(hour)]
        revenue=float(h.revenue.mean()) if len(h) else np.nan
        gp=float(h.gp.mean()) if len(h) else np.nan
        margin=revenue*(1-p['delivery_discount'])*(1-p['delivery_commission'])+p['delivery_fee']-(revenue-gp)-p['delivery_packaging']-p['delivery_courier']
        rows.append(dict(hour=hour,observed_baskets_daily=len(h)/days,observed_gp_daily=float(h.gp.sum()/days),
          delivery_margin_mix_proxy=margin,conditional_net_per_delivery=margin-(1-p['delivery_incremental'])*p['delivery_displaced_gp'],
          support='Observed in-store sales' if len(h) else 'No sales support: require external demand estimate'))
    return pd.DataFrame(rows)
