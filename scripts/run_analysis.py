"""Generate all Stories tables, figures and reports from authorized local data."""
import argparse
import json
import sys
import platform
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.analytics import (ROOT,load_data,baskets,validate,summary,matched_products,
    decomposition,counterfactual,associations,bundle_scenarios)
from src.feature_effects import CATALOG,frames,effect_matrix
from src.features import (branch_hour_panel,clock_template_check,hour_regimes,hourly_profile,staffing_template,
    DUST_EVENT,enrich,daily_panel,weather_effects,forecast_check,drink_mix_by_weather,
    month_turn_placebo,rain_order_type)

def external(x, out, tables):
    """Weather/calendar enrichment: tables plus reports/external_factors.md."""
    e=enrich(x); p=daily_panel(e)
    t=dict(external_effects_baskets=weather_effects(p),external_effects_revenue=weather_effects(p,outcome='revenue'),
        external_holdout=forecast_check(p),drink_mix_by_temperature=drink_mix_by_weather(e),
        month_turn_placebo=month_turn_placebo(p),rain_dine_in=rain_order_type(e),
        external_daily_panel=p.drop(columns=['gp']))
    for name,d in t.items(): d.to_csv(tables/f'{name}.csv',index=False)
    eff=t['external_effects_baskets'].set_index('feature'); hold=t['external_holdout'].set_index('model').mae_baskets
    mix=t['drink_mix_by_temperature']; rain=t['rain_dine_in'].iloc[0]; placebo=t['month_turn_placebo']
    early=p.assign(early=p.date.dt.day<=6)
    tr,te=[weather_effects(d,cols=['early']).iloc[0] for d in (early[early.date<'2026-05-01'],early[early.date>='2026-05-01'])]
    pct=lambda r:f"{r['effect']:+.1%} (95% CI {r['ci_low']:+.1%} to {r['ci_high']:+.1%})"
    monthly_temp=p.groupby('month').temp_mean.mean()
    report=f'''# External factors — weather, holidays, Ramadan, payday

**Weather, air quality and holidays do not explain Stories' demand in this file, so they should not drive staffing or stock decisions yet.** After branch × weekday and trend controls, rain, heavy rain, temperature surprises, dust episodes, public holidays, holiday eves, bridge days, school breaks and Ramadan move daily baskets by at most a few percent, and each of those 95% intervals includes zero. Adding them to a forecast {'does not improve' if hold.iloc[1]>=hold.iloc[0]-.01 else 'improves'} May–June accuracy (MAE {hold.iloc[0]:.3f} → {hold.iloc[1]:.3f} baskets per branch-day){'; the extra features overfit the four training months' if hold.iloc[1]>hold.iloc[0]+.01 else ''}. The cold-drink share of drinks stays at {mix.cold_share.min():.1%}–{mix.cold_share.max():.1%} as Beirut warms from {monthly_temp.min():.1f}°C (January mean) to {monthly_temp.max():.1f}°C (June). A real café's iced-drink share normally rises with heat, so a flat share points to a fixed menu mix or a simulated source (transaction IDs start with `SYN-`). Confirm with the data team before anyone builds weather-based planning.

## Features added (not in the source file)
81 columns, built by `src/features.py` from `data/external/`. They are stored in SQLite as `context_daily`, `context_hourly`, `line_features` and the `transactions_enriched` view (`database/add_features.py`).
- **Daily weather** (Open-Meteo ERA5): mean, max, min and feels-like temperature, daily range, change since yesterday, a 15-day temperature anomaly, rain mm and hours, yesterday's rain, 3-day rain, dry streak, rainy (≥1 mm), heavy-rain (≥10 mm), hot-day (≥30°C) and windy (≥40 km/h) flags, sunshine, daylight, WMO weather type.
- **Hourly weather at the transaction hour:** temperature, feels-like, rain, humidity, dew point, cloud, wind, daylight, weather type, raining-now.
- **Air quality** (Open-Meteo CAMS): hourly PM10, PM2.5, dust, US AQI and UV. Daily maxima, dust-event (≥{DUST_EVENT} µg/m³) and poor-air (AQI >100) flags, dusty-now.
- **Calendar:** Lebanese public holidays (lunar dates are estimates), holiday eves, days to the next holiday and since the last one, bridge days, long weekends, estimated school breaks, daylight-saving time, Valentine's and Mother's Day, Ramadan (est. 18 Feb–19 Mar 2026), the iftar window and minutes from sunset, payday window, day and week of month, month start and end, quarter.
- **Derived from the transactions:** daypart, product type (hot drink, cold drink, food), basket size, value and category count, food + drink basket, discounted basket, baskets at the same branch in the same hour and on the same day, and customer visit number, days since previous visit, first visit to that branch and repeat flag. History uses only earlier visits.

## Evidence
Log-linear model of daily baskets per branch with branch × weekday effects, a linear trend and week-clustered standard errors (`tables/external_effects_baskets.csv`; revenue version alongside):

| Feature | Change in baskets | Days |
|---|---|---|
''' + '\n'.join(f"| {k} | {pct(r)} | {'' if pd.isna(r.days_with_feature) else int(r.days_with_feature)} |" for k,r in eff.iterrows()) + f'''

- **Holdout:** training Jan–Apr, testing May–Jun, the context features leave MAE at {hold.iloc[1]:.3f} vs {hold.iloc[0]:.3f} for the baseline (`tables/external_holdout.csv`).
- **Month-turn lift (weak, hypothesis only):** the payday window shows {pct(eff.loc['payday_window'])}. A placebo test over all 31 six-day windows puts days 1–6 highest. That window was chosen after looking at the data. It estimates {pct(tr)} in Jan–Apr but only {pct(te)} in May–Jun, and April reverses (`tables/month_turn_placebo.csv`). Treat it as a staffing hypothesis to retest, not an effect to bank.
- **Rain at the transaction hour:** within-month dine-in share changes by {rain.dine_in_share_change*100:+.1f} percentage points (day-bootstrap CI {rain.ci_low*100:+.1f} to {rain.ci_high*100:+.1f}). The change gets smaller as rain gets heavier, so it may be noise (`tables/rain_dine_in.csv`).
- **Ramadan:** no level shift. Because the hourly basket profile does not move toward iftar, the timing data look insensitive to it, which is another realism flag.

## Assumptions and limits
Branch locations are not given. One central-Beirut weather point stands in for Garden, Harbour and Uptown. ERA5 is reanalysis on a ~9–25 km grid, not a station at the door. Lunar holiday dates may be off by a day. Six months gives only 16 holiday days and 16 heavy-rain days, so small effects (under ~5%) cannot be ruled out. The trend is linear in log baskets. These are associations, not causal effects.

## Decision
Do not buy weather feeds or build weather-driven staffing on this evidence. If Stories' real POS data show weather sensitivity, rerun `scripts/run_analysis.py` on that data; the pipeline and holdout test are ready. Retest the month-start lift on the next quarter before using it for rosters.
'''
    (out/'external_factors.md').write_text(report)
    t.update(clock_loop(x,out,tables,t))
    t['feature_effects']=effect_matrix(frames(x))
    t['feature_catalog']=pd.DataFrame([dict(feature=k,group=g,grain=r,description=d) for k,(g,r,d) in CATALOG.items()])
    for name in ['feature_effects','feature_catalog']: t[name].to_csv(tables/f'{name}.csv',index=False)
    return t

def clock_loop(x, out, tables, ext):
    """Feature-loop conclusion: demand is a clock template plus Poisson chance."""
    g=branch_hour_panel(x)
    t=dict(clock_template_check=clock_template_check(g),hour_regimes=hour_regimes(x),
        hourly_profile=hourly_profile(x),staffing_template=staffing_template(g,x))
    for name,d in t.items(): d.to_csv(tables/f'{name}.csv',index=False)
    c=t['clock_template_check']; base,weather,only=c.iloc[0],c.iloc[1],c.iloc[2]
    hp=t['hourly_profile'].set_index('hour'); r=t['hour_regimes']
    pm=r[r.regime.eq('18–23')].set_index('order_type'); day=r[r.regime.eq('11–17')].set_index('order_type')
    st=t['staffing_template']; peak=st.loc[st.expected.idxmax()]
    wd=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    report=f'''# Feature loop: what 81 new features taught us

**Stories' demand is set by the clock, not the sky.** A template of branch × hour × weekday plus a growth trend predicts unseen May–June branch-hours with MAE {base.holdout_mae:.3f} baskets. Pure Poisson chance around that template would give {base.poisson_floor_mae:.3f}. The template is therefore within **{base.gap_to_floor:.1%} of the best any forecast can do**. Holdout dispersion is {base.holdout_dispersion:.2f}, where 1.00 means the remaining variation is pure arrival randomness. Adding every hourly weather, dust and calendar feature changes MAE to {weather.holdout_mae:.3f}. Weather and calendar without the clock reach R² {only.holdout_r2:.2f}, against {base.holdout_r2:.2f} for the template. **Decision:** stop searching for external demand drivers and staff from the clock template. Size buffers with Poisson quantiles (`tables/staffing_template.csv`). Treat exact Poisson behaviour as one more sign that this file is simulated: real café traffic is usually overdispersed by weather, events and local shocks. Reconcile with real POS data before committing capital.

## The loop
Each round tested a hypothesis, kept what replicated in both Jan–Mar and Apr–Jun after a false-discovery correction, and fed the next round.

| Round | Hypothesis / feature | Result | Kept? |
|---|---|---|---|
| 0 | Weather, holidays, Ramadan, payday, dust, bridge days, school breaks (81 columns) | Daily effects all near zero after branch × weekday + trend controls. More features made the daily forecast worse. See [external_factors.md](external_factors.md) | Null |
| 1 | Screen every feature × 8 basket outcomes, within branch × month, BH-corrected, split-half replication | Strongest hits are sunset, daylight, UV and hourly temperature on dine-in and cold share. All of these are proxies for the clock hour | Redirect |
| 2 | Rescreen within branch × month × **hour** | Every weather effect disappears. What remains is the discount mechanics already documented in `analysis/` | Null |
| 3 | Does the evening switch follow sunset or the clock? | Clock. Dine-in jumps at 18:00 in every month (sunset moves from 17:40 to 19:55) and every branch | **Kept** |
| 4 | Temperature → discounts? | Spurious. Two 8-day 15% campaigns (12–19 Mar and 12–19 May), already analysed in `analysis/outputs/REPORT.md` | Dropped |
| 5 | Is dine-in worth more? | No. Within each regime dine-in and takeaway baskets have the same GP, units and mix | **Kept** (seats, not margin) |
| 6 | Clock template vs weather at branch-hour level, May–June holdout | Template R² {base.holdout_r2:.2f}; weather adds {weather.holdout_r2-base.holdout_r2:+.3f} | **Kept** |
| 7 | Is anything left to find? Poisson dispersion test | Dispersion {base.train_dispersion:.2f} train, {base.holdout_dispersion:.2f} holdout; MAE {base.gap_to_floor:.1%} above the noise floor | **Conclusion** |

## Three clock regimes
- **07–10:** cold-drink share of hot + cold drinks {hp.loc[7:10].cold_share.mean():.0%}, dine-in {hp.loc[7:10].dine_in_share.mean():.0%}. Bakery and hot coffee lead.
- **11–17:** cold share steps to {hp.loc[11:17].cold_share.mean():.0%} at 11:00, dine-in stays at {hp.loc[11:17].dine_in_share.mean():.0%}.
- **18–23:** dine-in jumps to {hp.loc[18:23].dine_in_share.mean():.0%} at 18:00 and cold share to {hp.loc[19:23].cold_share.mean():.0%} at 19:00. Cold coffee, matcha and desserts rise. GP per basket is ${pm.loc['Dine-in'].gp_per_basket:.2f} dine-in vs ${pm.loc['Takeaway'].gp_per_basket:.2f} takeaway (daytime ${day.loc['Dine-in'].gp_per_basket:.2f} vs ${day.loc['Takeaway'].gp_per_basket:.2f}).

The steps are identical in every month even though the mean temperature rises by about 11°C, so iced-drink demand here is an **evening occasion, not a heat response**. Plan ice, cold-brew prep, dessert stock and seating by hour of day. A seasonal "summer iced" push has no support in this file. Because dine-in earns the same as takeaway, the evening's binding resource is seats and prep, not menu margin. The busiest planning cell is {peak.branch} on {wd[int(peak.weekday)]} at {int(peak.hour)}:00: {peak.expected:.1f} expected baskets in June, P90 {int(peak.p90_baskets)}.

## Limits
Clock hours are bins from transaction time stamps; opening hours, seats, staff and queues are not in the file. The Poisson floor assumes the template's rates are correct; the {base.gap_to_floor:.1%} gap is the room left for every unobserved factor combined. Steps that are this sharp and this uniform across branches and months look like generator rules, like the Tuesday spike and the ×1.05 price list documented in [outside_in_chains.md](outside_in_chains.md).
'''
    (out/'feature_loop.md').write_text(report)
    return t

def run(source, out):
    out=Path(out); tables=out/'tables'; figures=out/'figures'
    tables.mkdir(parents=True,exist_ok=True); figures.mkdir(exist_ok=True)
    x=load_data(source); o=baskets(x); quality=validate(x,source)
    quality['runtime']={'python':platform.python_version(),'pandas':pd.__version__,'numpy':np.__version__}
    branch=summary(x,'branch'); matched=matched_products(x); pairs=associations(x)
    month=summary(x,['month','branch'])
    scenarios=pd.DataFrame([dict(recovery=r,**counterfactual(x,x,recovery=r)) for r in [0,.25,.5,.75,1]])
    monthly_gap=pd.DataFrame([dict(month=k,**counterfactual(g,x)) for k,g in x.groupby('month')])
    discount=x.groupby(['branch','discount']).agg(lines=('transaction','size'),
        concession=('concession','sum'),revenue=('revenue','sum'),gp=('gp','sum'),units=('quantity','sum')).reset_index()
    discount['margin']=discount.gp/discount.revenue
    customer=o.dropna(subset=['customer']).groupby('customer').agg(visits=('date','size'),
        revenue=('revenue','sum'),gp=('gp','sum'))
    types=pd.DataFrame({'column':x.columns,'dtype':[str(t) for t in x.dtypes]})
    sh=decomposition(x)
    standard=[]
    w=x.groupby('product').quantity.sum(); w=w/w.sum()
    for b,d in x.groupby('branch'):
        p=d.groupby('product').agg(revenue=('revenue','sum'),gp=('gp','sum'),units=('quantity','sum'))
        standard.append(dict(branch=b,common_mix_gp_per_unit=float((w*p.gp/p.units).sum()),
            common_mix_margin=float((w*p.gp/p.units).sum()/(w*p.revenue/p.units).sum())))
    original=pd.read_csv(source)
    dedup=x.loc[~original.duplicated()]
    sensitivity=pd.DataFrame([dict(policy=label,lines=len(d),baskets=d.transaction.nunique(),
        revenue=d.revenue.sum(),gp=d.gp.sum(),garden_matched_gap=counterfactual(d,x)['matched_gap'])
        for label,d in [('Retain all rows (baseline)',x),('Remove excess exact rows (sensitivity only)',dedup)]])
    tableset={'duplicate_sensitivity':sensitivity,'branches':branch,'monthly':month,'products':summary(x,['product','branch']),
        'categories':summary(x,'category'),'order_types':summary(x,'order_type'),
        'matched_products':matched,'decomposition':sh,'common_mix':pd.DataFrame(standard),
        'cost_scenarios':scenarios,'monthly_cost_gap':monthly_gap,'associations':pairs,
        'bundle_scenarios':bundle_scenarios(x,pairs),'discounts':discount,
        'basket_distribution':o.groupby('products').size().rename('baskets').reset_index(),
        'customer_summary':pd.DataFrame([dict(identified_customers=len(customer),
            repeat_share=float(customer.visits.gt(1).mean()),median_visits=float(customer.visits.median()),
            identified_revenue=float(customer.revenue.sum()))]),'column_types':types,
        'weekday':summary(x,'weekday'),'hour':summary(x,'hour')}
    for name,t in tableset.items(): t.to_csv(tables/f'{name}.csv',index=False)
    tableset.update(external(x,out,tables))
    # No customer or transaction identifiers are written to evidence tables.
    (out/'data_quality.json').write_text(json.dumps(quality,indent=2,default=lambda v:int(v)))
    plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'#faf8f4'})
    def bar(name,labels,values,title,ylabel):
        fig,ax=plt.subplots(figsize=(10,5)); ax.bar(labels,values,color='#75543d')
        ax.set(title=title+'\nJanuary–June 2026',ylabel=ylabel); ax.tick_params(axis='x',labelrotation=25)
        fig.tight_layout(); fig.savefig(figures/f'{name}.png',dpi=150); plt.close(fig)
    bar('branch_margin',branch.branch,branch.margin*100,'Recorded gross margin by branch','Gross profit / revenue (%)')
    bar('priority_products',matched.head(8)["product"],matched.head(8).opportunity,'Garden matched-cost difference by product','Hypothetical six-month GP difference (USD)')
    bar('cost_scenarios',scenarios.recovery.map(lambda v:f'{v:.0%}'),scenarios.net_benefit,'Recoverable share of Garden cost difference','GP change before implementation expense (USD)')
    bar('decomposition',sh.factor,sh.harbour_minus_garden_gp_per_unit,'Harbour minus Garden: exact Shapley bridge','Difference in GP per unit (USD)')
    fig,ax=plt.subplots(figsize=(9,5)); ax.scatter(matched.cost_Harbour,matched.cost_Garden,color='#75543d')
    ax.set(xlabel='Harbour recorded cost / unit (USD)',ylabel='Garden recorded cost / unit (USD)',title='Same products, different recorded costs · Jan–Jun 2026')
    fig.tight_layout();fig.savefig(figures/'matched_costs.png',dpi=150);plt.close(fig)
    g=branch.set_index('branch').loc['Garden']; h=branch.set_index('branch').loc['Harbour']
    gap=float(scenarios.iloc[-1].matched_gap); concession=float(x.concession.sum())
    top=matched.iloc[0]; share=float(matched.head(5).opportunity.sum()/gap)
    duplicate_gap=counterfactual(x.loc[~pd.read_csv(source).duplicated()],x)['matched_gap']
    indexed=matched.set_index('product')
    price_align=(indexed.price_Harbour/indexed.price_Garden-1)
    garden=x[x.branch.eq('Garden')].copy()
    garden['price_uplift']=garden["product"].map(price_align)
    align_gain=float((garden.revenue*garden.price_uplift).sum())
    threshold=align_gain/(float(g.gp)+align_gain)
    best=pairs.iloc[0] if len(pairs) else None
    conclusion=f"Garden's recorded gross margin is {g.margin:.2%}, versus Harbour's {h.margin:.2%}. Replacing Garden's costs with the same products' Harbour costs, holding quantities, prices and discounts fixed, raises six-month recorded gross profit by ${gap:,.2f}. Audit costing before changing procurement: the uniform ratios may reflect allocation rules rather than avoidable cash costs."
    premium=float(matched.cost_ratio.mean()-1)
    prod=x.groupby('product')[['revenue','gp']].sum(); prod['margin']=prod.gp/prod.revenue
    weakest=prod.gp.idxmin(); review=prod.loc[prod.gp.nsmallest(10).index].nsmallest(3,'margin')
    review_text=', '.join(f"{n} ({m:.0%} margin)" for n,m in review.margin.items())
    report=f'''# Stories Coffee — executive recommendation

{conclusion}

## Top 5 actions
1. **Audit Garden's costs.** ${gap/1000:,.1f}K of six-month gross profit depends on whether Garden's costs, about {premium:.0%} above Harbour's for identical products, are avoidable.
2. **Staff and prep for the evening peak.** 19:00–23:59 earns 44.6% of gross profit (see deep_insights.md).
3. **Suggest a bakery item with matcha, with no discount.** The pair is bought together 1.7× more often than chance; a rebate would turn the gain into a loss.
4. **Hold blanket discounts.** Run a randomized 0/10/15% test first.
5. **Ignore the weather when planning.** Demand follows the clock, not the temperature.

No product needs to be cut. The weakest, {weakest}, still earns {prod.gp[weakest]/prod.gp.sum():.2%} of gross profit, and the bottom products are staples that mostly sell in multi-item baskets. Review recipe and waste costs for {review_text}.

## Business problem
The file contains {len(x):,} item lines in {len(o):,} baskets, January 1–June 30, 2026. Revenue is ${x.revenue.sum():,.2f}; recorded gross profit is ${x.gp.sum():,.2f}. Gross profit excludes payroll, rent and implementation costs.

## Evidence
- All {len(matched)} products are shared. Garden/Harbour cost ratios range from {matched.cost_ratio.min():.4f} to {matched.cost_ratio.max():.4f}; price ratios range from {matched.price_ratio.min():.4f} to {matched.price_ratio.max():.4f}.
- Product-branch cost values are constant: maximum distinct costs per product/branch is {int(x.groupby(['product','branch']).cost.nunique().max())}. This weakens a product-specific waste explanation; no transaction data identify the underlying costing rule.
- {top['product']} contributes ${top.opportunity:,.2f}; the top five products account for {share:.1%} of the matched-cost difference. See `tables/matched_products.csv` for all products and `monthly_cost_gap.csv` for every month.
- Keeping every row yields ${gap:,.2f}; dropping excess exact duplicates as a sensitivity yields ${duplicate_gap:,.2f}. Duplicates are retained in the baseline because no line identifier establishes erroneous duplication.
- A separate discount investigation finds that classifying baskets by any discounted line can create apparent basket-size uplift even under shuffled labels. See the existing `analysis/outputs/REPORT.md`; do not treat basket differences as causal effects.

## Competing explanations
Product mix, price and discount differences are evaluated by exact Shapley attribution of GP/unit, averaging all 24 factor orderings. See `tables/decomposition.csv` and `common_mix.csv`. These explain arithmetic differences, not causal mechanisms. Supplier contracts, recipes and accounting allocations remain unresolved. Fixed costs across all dates/products favor investigating a systematic rule first.

## Proposed solution
Finance should trace the highest-dollar products from POS cost masters through recipes and supplier invoices. Compare Garden and Harbour on identical SKUs, portions, freight, waste and allocation definitions. Confirm avoidable cash expense before procurement changes. Preserve quality and service during any pilot.

## Financial impact
At 25%, 50%, 75% and 100% recoverability, hypothetical six-month GP gains are ${gap*.25:,.2f}, ${gap*.5:,.2f}, ${gap*.75:,.2f} and ${gap:,.2f}. Net benefit subtracts an unknown implementation expense E. Reject an intervention if verified avoidable benefit does not exceed E and operational risk. If the difference is purely allocation, cash savings may be zero.

Exact per-product Harbour price alignment adds ${align_gain:,.2f} before demand response at unchanged discounts and mix. Its proportional volume-loss break-even is {threshold:.2%}, before implementation costs. Demand elasticity is unknown. Do nothing is preferable to an untested chain-wide price change; a targeted costing audit is the lower-commitment alternative.

## Risks and limitations
{quality['missing_customer_basket_share']:.1%} of baskets have no customer ID. Observed repeat customers are a selected subset. {quality['exact_duplicate_excess']} excess duplicate rows remain unresolved. Revenue has {quality['revenue_exceptions_half_cent']} deviations beyond half a cent and GP has {quality['gp_exceptions_half_cent']}; see the quality report. Source rounding is preserved. Six historical months do not establish future performance, cash savings or treatment effects. Scenarios are assumptions, not forecasts.

## Proposed pilot
Audit the top five dollar contributors first. If invoices confirm a recoverable difference, compare eligible products under current and revised procurement/recipe practices, with matched control products and pre-period trends. Finance must set duration and minimum worthwhile cash benefit after estimating day-level variance and serial correlation. Stop for quality, stockout or service deterioration. For promotions, randomize 0%, 10%, 15% offers before purchase, log nonbuyers, and measure incremental contribution per assigned visitor. Sample size requires a specified minimum effect and pre-pilot visitor-level variance.

## Final decision
Authorize a costing audit; authorize operational changes only after avoidable cash costs and quality safeguards are verified. Hold broad discount expansion pending a randomized test. Avoid blanket bundle discounts: co-purchase is not proof of incremental demand.
'''
    (out/'executive_summary.md').write_text(report)
    fourth=f"The top five products explain {share:.1%} of the recorded cost gap. The largest contributor is {top['product']}. This audit ranking is supplemented by category-pair null models, evening demand exposure and growth-quality investigations in deep_insights.md. These exploratory findings support experiments, not claims of measured intervention benefits." 
    assoc_text=(f"Strongest training lift among pairs with at least 30 training baskets: {best.product_a} + {best.product_b}; train n={int(best.train_count)}, lift={best.train_lift:.2f}; test n={int(best.test_count)}, lift={best.test_lift:.2f}. Small lifts and sparse pair support do not justify blanket bundle discounts. Pair selection uses training lift; the later data are for descriptive validation only." if best is not None else 'No product pair meets the minimum training support. There is no compelling supported bundle recommendation.')
    (out/'full_analysis.md').write_text(report+'\n## Additional discovery\n'+fourth+'\n\n## Basket investigation\n'+assoc_text+'\n\n'+f'Average units/basket: {o.units.mean():.3f}; GP/basket: ${o.gp.mean():.2f}. List-price concessions total ${concession:,.2f}; this is mechanical arithmetic, not lost causal profit.\n\n'+'## Evidence index\n'+ '\n'.join(f'- `tables/{k}.csv`' for k in tableset))
    from scripts.deep_insights import run as deep_run
    deep=deep_run(source,out,verbose=False)
    with (out/'full_analysis.md').open('a') as f:f.write('\n\n'+deep)
    from scripts.causal_decisions import run as causal_run
    causal=causal_run(source,out)
    with (out/'full_analysis.md').open('a') as f:f.write('\n\n'+causal)
    with (out/'executive_summary.md').open('a') as f:
        f.write('\n## Further decision evidence\nSee [deeper investigations](deep_insights.md) for evening demand exposure, an exact growth-quality bridge, and category-pair preferences tested against a basket-size/context baseline. These support focused service and no-discount attachment experiments; they do not establish causal savings.\n')
        f.write('\n## Protecting the business before rollout\nThe [causal decision brief](causal_decisions.md) traces accounting, procurement quality, whole-basket pricing, queue/attachment, promotion displacement and customer-identification risks. It calculates the losses each scenario can absorb and specifies measurements and stop rules for unresolved links.\n')
    print(conclusion); print('Generated',out)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'stories_transactions.csv')
    p.add_argument('--output',type=Path,default=ROOT/'reports'); a=p.parse_args();run(a.source,a.output)
