"""Explore drink associations with 30-day non-return; no causal discontinuation claim.

One first drink-containing order per identified customer in each index month.
Only aggregate product results are written; customer identifiers stay in memory.
Requires numpy; no fitting libraries or network access.
"""
import csv
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, date
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DRINKS = {'Hot Coffee', 'Cold Coffee', 'Cold Drinks', 'Matcha & Tea'}


def fit_logit(x, y):
    """Unpenalized Newton fit with likelihood line search and observed information."""
    beta = np.zeros(x.shape[1])
    def likelihood(b):
        z = x @ b
        return np.sum(y * z - np.logaddexp(0, z))
    for _ in range(80):
        p = 1 / (1 + np.exp(-np.clip(x @ beta, -35, 35)))
        info = x.T @ ((p * (1-p))[:, None] * x)
        step = np.linalg.solve(info, x.T @ (y-p))
        scale = 1
        while likelihood(beta + scale*step) < likelihood(beta)-1e-10 and scale > 1/4096:
            scale /= 2
        beta += scale*step
        if np.max(np.abs(scale*step)) < 1e-8:
            p = 1 / (1 + np.exp(-np.clip(x @ beta, -35, 35)))
            covariance = np.linalg.inv(x.T @ ((p * (1-p))[:, None] * x))
            return beta, np.sqrt(np.diag(covariance))
    raise ValueError('Logistic model did not converge')


def bh(values):
    result = [1.0]*len(values)
    best = 1.0
    for rank, i in reversed(list(enumerate(sorted(range(len(values)), key=lambda i: values[i]), 1))):
        best = min(best, values[i]*len(values)/rank)
        result[i] = min(1, best)
    return result


def wilson(k, n):
    p=k/n; z=1.95996398454; den=1+z*z/n
    middle=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return middle-half, middle+half


def load():
    db=sqlite3.connect(f'file:{ROOT / "database/stories.sqlite"}?mode=ro',uri=True)
    orders={}
    for oid,day,clock,branch,customer,revenue in db.execute('SELECT transaction_id,order_date,order_time,branch,customer_id,order_revenue_usd FROM orders WHERE customer_id IS NOT NULL'):
        orders[oid]=dict(id=oid,when=datetime.fromisoformat(day+'T'+clock),branch=branch,customer=customer,revenue=revenue,drinks=set())
    products=set()
    for oid,product,category in db.execute('SELECT transaction_id,product,category FROM transaction_lines'):
        if oid in orders and category in DRINKS:
            orders[oid]['drinks'].add(product)
            products.add(product)
    customers=defaultdict(list)
    for row in orders.values(): customers[row['customer']].append(row)
    for visits in customers.values(): visits.sort(key=lambda row:(row['when'],row['id']))
    last_day=date.fromisoformat(db.execute('SELECT MAX(order_date) FROM orders').fetchone()[0])
    db.close()
    return customers, sorted(products), last_day


def cohort(customers, month, last_day):
    result=[]
    for visits in customers.values():
        index=next((v for v in visits if v['when'].month==month and v['drinks']),None)
        if index is None: continue
        day=index['when'].date()
        assert day+timedelta(days=30)<=last_day
        prior=[v for v in visits if index['when']-timedelta(days=90)<=v['when']<index['when']]
        previous=[v for v in visits if v['when']<index['when']]
        recency=min(90,(day-previous[-1]['when'].date()).days) if previous else 90
        returned=any(day<v['when'].date()<=day+timedelta(days=30) for v in visits)
        result.append(dict(drinks=index['drinks'],lost=int(not returned),branch=index['branch'],week=(day.day-1)//7,
                           frequency=math.log1p(len(prior)),recency=recency,new=int(not previous),
                           prior_spend=math.log1p(sum(v['revenue'] for v in prior)/len(prior)) if prior else 0))
    return result


def analyze(cohort, products):
    y=np.array([r['lost'] for r in cohort],dtype=float)
    columns=[np.ones(len(y))]
    for key in ['frequency','recency','new','prior_spend']:
        a=np.array([r[key] for r in cohort],dtype=float)
        if a.std()>0: columns.append((a-a.mean())/a.std())
    for key in ['branch','week']:
        for level in sorted({r[key] for r in cohort})[1:]: columns.append(np.array([r[key]==level for r in cohort],dtype=float))
    controls=np.column_stack(columns)
    output=[]
    for product in products:
        exposure=np.array([product in r['drinks'] for r in cohort],dtype=float)
        n=int(exposure.sum());k=int(y[exposure==1].sum())
        if not n: continue
        low,high=wilson(k,n)
        row=dict(product=product,customers=n,no_return_30d=k,no_return_rate=k/n,rate_ci_low=low,rate_ci_high=high,
                 adjusted_odds_ratio='',odds_ci_low='',odds_ci_high='',p_value='',q_value='',model_status='Too few outcomes for adjusted model')
        if n>=30 and min(k,n-k)>=5:
            try:
                beta,se=fit_logit(np.column_stack([controls,exposure]),y)
                row.update(adjusted_odds_ratio=math.exp(beta[-1]),odds_ci_low=math.exp(beta[-1]-1.96*se[-1]),
                           odds_ci_high=math.exp(beta[-1]+1.96*se[-1]),p_value=math.erfc(abs(beta[-1]/se[-1])/math.sqrt(2)),model_status='Exploratory adjusted association')
            except (ValueError,np.linalg.LinAlgError,OverflowError): row['model_status']='Model unstable; descriptive result only'
        output.append(row)
    fitted=[r for r in output if r['p_value']!='']
    for r,q in zip(fitted,bh([r['p_value'] for r in fitted])):r['q_value']=q
    return sorted(output,key=lambda r:-r['no_return_rate'])


def main():
    # Validate the fitter against the exact unadjusted 2x2 odds-ratio formula.
    y=np.array([1]*20+[0]*30+[1]*10+[0]*40,dtype=float)
    x=np.column_stack([np.ones(100),np.array([1]*50+[0]*50)])
    beta,se=fit_logit(x,y)
    assert abs(math.exp(beta[1])-(20*40)/(30*10))<1e-7
    assert abs(se[1]-math.sqrt(1/20+1/30+1/10+1/40))<1e-7
    customers,products,last_day=load()
    may=cohort(customers,5,last_day);april=cohort(customers,4,last_day)
    results=analyze(may,products);april_results={r['product']:r for r in analyze(april,products)}
    inactive=[v for v in customers.values() if (last_day-v[-1]['when'].date()).days>=30]
    last_drinks=defaultdict(int);with_drink=0
    for visits in inactive:
        last=next((v for v in reversed(visits) if v['drinks']),None)
        if last:
            with_drink+=1
            for product in last['drinks']:last_drinks[product]+=1
    for row in results:
        row['last_drink_among_inactive_customers']=last_drinks[row['product']]
        check=april_results.get(row['product'],{})
        row['april_customers']=check.get('customers','');row['april_no_return_rate']=check.get('no_return_rate','')
        row['april_adjusted_odds_ratio']=check.get('adjusted_odds_ratio','')
    destination=ROOT/'reports/tables/drink_30day_return.csv'
    with destination.open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    overall=sum(r['lost'] for r in may)/len(may)
    flagged=[r for r in results if r['q_value']!='' and r['q_value']<.05 and r['adjusted_odds_ratio']>1]
    lines=['# Last drinks and 30-day return behavior','',
           f'**Decision: no drink should be discontinued from this analysis alone.** {len(flagged)} drink(s) have a higher adjusted non-return association after a 5% false-discovery correction in the May cohort. Associations are not causes.','',
           f'The data ends {last_day}. Of {len(customers):,} identified customers, {len(inactive):,} had made no purchase in the last 30 days; {with_drink:,} of these had at least one recorded drink order. Their latest drink-containing basket is counted descriptively. A basket can contain several drinks, so counts overlap. Customers can return after the file ends.','',
           '## A fairer comparison than ranking final drinks','',
           f'Use one first drink-containing order in May per identified customer ({len(may):,} customers). Follow every index purchase for 30 complete calendar days; a return is any identified purchase on a later date within that window, including food-only orders. Overall non-return was {overall:.1%}. June index purchases are excluded because their full follow-up is unavailable.','',
           'Each drink is compared with other drink baskets, adjusting for branch, week within May, prior-90-day purchase frequency and average basket spend, time since the preceding purchase, and whether the customer has any earlier observed visit. These histories are only what this file observes. Each model uses one row per customer. Multiple drinks on one order create overlapping exposures. Odds ratios are not relative risks.','',
           'Unpenalized logistic models require at least 30 exposed customers and five outcomes of each kind. Wald intervals and tests are exploratory; Benjamini–Hochberg correction covers all successfully fitted May product tests. April uses the same design as a consistency check, not independent replication because customers can overlap.','',
           '| Drink | May customers | No return within 30 days | Adjusted odds ratio (95% interval) | Adjusted q | Inactive customers’ last drink |',
           '|---|---:|---:|---:|---:|---:|']
    for r in results:
        effect=f"{r['adjusted_odds_ratio']:.2f} ({r['odds_ci_low']:.2f}–{r['odds_ci_high']:.2f})" if r['adjusted_odds_ratio']!='' else 'Insufficient sample / unstable'
        q=f"{r['q_value']:.3f}" if r['q_value']!='' else 'n.a.'
        lines.append(f"| {r['product']} | {r['customers']} | {r['no_return_rate']:.1%} | {effect} | {q} | {r['last_drink_among_inactive_customers']} |")
    lines+=['','## What would justify a menu decision?','',
            'Use a repeatedly elevated association to prioritize a quality and recipe audit, complaints review, stockout check and comparison of customer mix. Then run a limited controlled recipe or menu-placement test. Track repeat visits, total gross profit, customer satisfaction and substitution into other products. Removing a profitable drink can lose loyal customers; customer preference and visit frequency can explain an observational association.','',
            'Customer IDs are missing on 36.5% of orders. Anonymous customers cannot be tracked, and identification may be selective. Non-return within 30 days is not permanent churn. No satisfaction ratings, complaints, stockouts, acquisition channels or reasons for leaving are recorded. All source rows are retained, including possible duplicate item lines; drink exposures use distinct product presence.','',
            'Source: `database/stories.sqlite`. Reproduce with `python scripts/drink_return_analysis.py` in an environment with NumPy. Aggregate results: `reports/tables/drink_30day_return.csv`. No customer IDs are exported.']
    (ROOT/'reports/drink_return_analysis.md').write_text('\n'.join(lines)+'\n')
    print(f'May cohort: {len(may)}; 30-day non-return: {overall:.1%}; inactive: {len(inactive)}; higher-risk FDR flags: {len(flagged)}')
    for row in results[:6]:print(row)
    print('Most common last drinks:',sorted(last_drinks.items(),key=lambda x:-x[1])[:5])


if __name__=='__main__':main()
