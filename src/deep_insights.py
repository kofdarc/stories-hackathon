"""Decision-led investigations: basket-size nulls, demand exposure and growth."""
from itertools import combinations
import numpy as np
import pandas as pd
from .analytics import baskets, summary


def category_null(x, draws=399, seed=490):
    """Shuffle category labels within context, preserving every basket's line count.

    This is an exploratory independence diagnostic, not randomized offer evidence.
    Repeated categories per basket are reduced to presence for pair counting.
    """
    categories=sorted(x.category.unique())
    pairs=list(combinations(range(len(categories)),2))
    if not pairs or x.empty: return pd.DataFrame()
    d=x.reset_index(drop=True).copy()
    ids,names=pd.factorize(d.transaction,sort=True)
    labels=pd.Categorical(d.category,categories=categories).codes
    lookup=np.array([[bool(mask & (1<<a)) and bool(mask & (1<<b)) for a,b in pairs]
                     for mask in range(1<<len(categories))],dtype=np.int64)
    def presence(z):
        masks=np.zeros(len(names),dtype=np.int64)
        np.bitwise_or.at(masks,ids,np.left_shift(1,z.astype(np.int64)))
        return masks
    def count(z):
        return np.bincount(presence(z),minlength=len(lookup)) @ lookup
    observed=count(labels)
    d['daypart']=d.hour//4
    groups=[g.index.to_numpy() for _,g in d.groupby(['branch','month','order_type','daypart'])]
    rng=np.random.default_rng(seed); null=np.zeros((draws,len(pairs)))
    for rep in range(draws):
        shuffled=labels.copy()
        for group in groups: shuffled[group]=rng.permutation(labels[group])
        null[rep]=count(shuffled)
    masks=presence(labels)
    singles=np.array([np.count_nonzero(masks & (1<<a)) for a in range(len(categories))])
    rows=[]
    for j,(a,b) in enumerate(pairs):
        mean=null[:,j].mean()
        rows.append(dict(category_a=categories[a],category_b=categories[b],baskets=len(names),
            a_baskets=int(singles[a]),b_baskets=int(singles[b]),pair_baskets=int(observed[j]),
            raw_lift=observed[j]*len(names)/(singles[a]*singles[b]),
            expected_pairs=float(mean),conditional_enrichment=observed[j]/mean if mean else np.nan,
            null_low=float(np.quantile(null[:,j],.025)),null_high=float(np.quantile(null[:,j],.975)),
            enrichment_p=(1+np.count_nonzero(null[:,j]>=observed[j]))/(draws+1)))
    t=pd.DataFrame(rows)
    ordered=np.argsort(t.enrichment_p.to_numpy()); m=len(t)
    adjusted=np.minimum.accumulate((t.enrichment_p.to_numpy()[ordered]*m/np.arange(1,m+1))[::-1])[::-1]
    t['enrichment_q']=np.nan;t.loc[ordered,'enrichment_q']=np.minimum(adjusted,1)
    return t.sort_values('conditional_enrichment',ascending=False)


def daypart_economics(x):
    """Financial exposure, not actual lost sales or optimal staffing estimates."""
    o=baskets(x).reset_index()
    o['period']=np.select([o.hour.between(7,10),o.hour.between(19,23)],
                         ['Morning 07–10','Evening 19–23'],default='Other 11–18')
    t=o.groupby(['branch','period']).agg(baskets=('transaction','size'),gp=('gp','sum'),
        revenue=('revenue','sum'),days=('date','nunique')).reset_index()
    t['hours_per_day']=t.period.map({'Morning 07–10':4,'Evening 19–23':5,'Other 11–18':8})
    t['gp_per_basket']=t.gp/t.baskets
    t['baskets_per_observed_day_hour']=t.baskets/(t.days*t.hours_per_day)
    t['gp_per_observed_day_hour']=t.gp/(t.days*t.hours_per_day)
    t['basket_share_within_branch']=t.baskets/t.groupby('branch').baskets.transform('sum')
    t['gp_share_within_branch']=t.gp/t.groupby('branch').gp.transform('sum')
    return t


def growth_bridge(x):
    """Exact two-factor symmetric bridge of first-to-last monthly GP per day."""
    o=baskets(x)
    monthly=o.groupby('month').agg(baskets=('gp','size'),gp=('gp','sum'),revenue=('revenue','sum'))
    monthly['calendar_days']=[pd.Period(k).days_in_month for k in monthly.index]
    monthly['baskets_per_day']=monthly.baskets/monthly.calendar_days
    monthly['gp_per_basket']=monthly.gp/monthly.baskets
    monthly['gp_per_day']=monthly.gp/monthly.calendar_days
    monthly['revenue_per_basket']=monthly.revenue/monthly.baskets
    a,b=monthly.iloc[0],monthly.iloc[-1]
    volume=(b.baskets_per_day-a.baskets_per_day)*(a.gp_per_basket+b.gp_per_basket)/2
    economics=(b.gp_per_basket-a.gp_per_basket)*(a.baskets_per_day+b.baskets_per_day)/2
    bridge=pd.DataFrame([dict(factor='More baskets per calendar day',gp_per_day_change=volume),
                         dict(factor='Changed GP per basket',gp_per_day_change=economics)])
    # Equal weekday weighting reduces different month-calendar compositions.
    daily=o.groupby(['date','month','weekday']).agg(baskets=('gp','size'),gp=('gp','sum')).reset_index()
    adjusted=daily.groupby(['month','weekday'])[['baskets','gp']].mean().groupby('month').mean()
    adjusted.columns=['weekday_standardized_baskets_per_day','weekday_standardized_gp_per_day']
    monthly=monthly.join(adjusted)
    return monthly.reset_index(),bridge


def basket_economics_uncertainty(x, draws=1999, seed=493):
    """Circular seven-day block bootstrap for first/last month GP per basket."""
    o=baskets(x).reset_index()
    daily=o.groupby(['month','date']).agg(gp=('gp','sum'),baskets=('transaction','size')).reset_index()
    months=sorted(daily.month.unique());rng=np.random.default_rng(seed);estimates=[]
    for month in [months[0],months[-1]]:
        d=daily[daily.month.eq(month)].sort_values('date');n=len(d)
        starts=rng.integers(0,n,size=(draws,int(np.ceil(n/7))))
        ids=((starts[:,:,None]+np.arange(7))%n).reshape(draws,-1)[:,:n]
        estimates.append(d.gp.to_numpy()[ids].sum(axis=1)/d.baskets.to_numpy()[ids].sum(axis=1))
    delta=estimates[1]-estimates[0]
    return dict(first_month=months[0],last_month=months[-1],block_days=7,draws=draws,
                low=float(np.quantile(delta,.025)),high=float(np.quantile(delta,.975)))


def attachment_cases(x, a='Matcha & Tea', b='Bakery'):
    """One B unit per newly attached A-only basket; explicit existing-pair leakage."""
    ids_a=set(x.loc[x.category.eq(a),'transaction']);ids_b=set(x.loc[x.category.eq(b),'transaction'])
    eligible=len(ids_a-ids_b); existing=len(ids_a&ids_b)
    target=x[x.category.eq(b)]
    if target.empty:return pd.DataFrame()
    gp=float(target.gp.sum()/target.quantity.sum());price=float(target.list_value.sum()/target.quantity.sum())
    rows=[]
    for discount in [0.,.1]:
        for adoption in [.01,.03,.05]:
            rebate=price*discount
            before_cost=eligible*adoption*(gp-rebate)-existing*rebate
            rows.append(dict(anchor=a,attached=b,eligible_a_only_baskets=eligible,existing_pairs=existing,
                assumed_adoption=adoption,assumed_rebate_rate=discount,attached_unit_gp=gp,
                rebate_per_unit=rebate,hypothetical_gp_before_expense=before_cost,
                break_even_adoption=existing*rebate/(eligible*(gp-rebate)) if eligible and gp>rebate else np.nan))
    return pd.DataFrame(rows)
