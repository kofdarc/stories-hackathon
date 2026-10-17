"""Rebuild the deeper discovery report and diagnostic evidence."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.analytics import ROOT,load_data,baskets
from src.deep_insights import category_null,daypart_economics,growth_bridge,attachment_cases,basket_economics_uncertainty

def run(source=ROOT/'stories_transactions.csv',out=ROOT/'reports',verbose=True):
    x=load_data(source);out=Path(out);tables=out/'tables';tables.mkdir(exist_ok=True,parents=True)
    training=category_null(x[x.date<'2026-05-01'])
    replication=category_null(x[x.date>='2026-05-01'],seed=491)
    pairs=training.merge(replication,on=['category_a','category_b'],suffixes=('_train','_replication'))
    pairs=pairs.sort_values('conditional_enrichment_train',ascending=False)
    pairs.to_csv(tables/'category_pair_null.csv',index=False)
    # Robustness: remove uncertain duplicate rows; keep all rows in baseline.
    raw=pd.read_csv(source)
    sensitivity=category_null(x.loc[~raw.duplicated()],seed=492)
    sensitivity.to_csv(tables/'category_pair_duplicate_sensitivity.csv',index=False)
    parts=daypart_economics(x);parts.to_csv(tables/'daypart_economics.csv',index=False)
    month,bridge=growth_bridge(x)
    interval=basket_economics_uncertainty(x)
    pd.DataFrame([interval]).to_csv(tables/'growth_block_bootstrap.csv',index=False)
    month.to_csv(tables/'growth_economics.csv',index=False);bridge.to_csv(tables/'growth_bridge.csv',index=False)
    attach=attachment_cases(x);attach.to_csv(tables/'attachment_decisions.csv',index=False)
    o=baskets(x);eve=o[o.hour.between(19,23)];morn=o[o.hour.between(7,10)]
    selected=pairs[(pairs.category_a.eq('Bakery')) & (pairs.category_b.eq('Matcha & Tea'))].iloc[0]
    a,b=month.iloc[0],month.iloc[-1]
    share=bridge.iloc[0].gp_per_day_change/bridge.gp_per_day_change.sum()
    no_discount=attach[(attach.assumed_adoption.eq(.03)) & attach.assumed_rebate_rate.eq(0)].iloc[0]
    paid=attach[(attach.assumed_adoption.eq(.03)) & attach.assumed_rebate_rate.eq(.1)].iloc[0]
    top=pairs.iloc[0]
    text=f'''# Stories Coffee — deeper decision insights

The practical opportunity is to **protect evening service and test targeted, no-discount attachment**, while finance audits Garden's recorded costs. Sales growth alone does not show better basket economics. Conventional association-rule lift can also miss pair preferences because the typical basket is small. These are measured diagnostics and proposed experiments, not measured treatment benefits.

## 1. A coffee business with an evening service risk

**Observed:** 19:00–23:59 accounts for {len(eve):,} baskets ({len(eve)/len(o):.1%}) and ${eve.gp.sum():,.2f} recorded GP ({eve.gp.sum()/o.gp.sum():.1%}). 07:00–10:59 contributes {len(morn):,} baskets ({len(morn)/len(o):.1%}) and ${morn.gp.sum():,.2f} GP. The five evening hours handle {len(eve)/5/(len(morn)/4):.2f} times as many baskets per nominal clock-hour as the four morning hours. All branches show this pattern; see daypart_economics.csv. These periods are explicit clock-hour bins, not inferred opening hours.

**Why this changes a decision:** copying the reference shop's morning-heavy staffing narrative would misallocate attention. Inspect queues, stockouts and labor deployment around the evening peak before adding morning promotions or cutting late coverage. The file does not contain staffing, waiting times, capacity or missed customers, so it cannot establish understaffing or recommend headcount cuts.

**Financial gate:** evening GP per observed basket is ${eve.gp.mean():.2f}. For an incremental staffing cost C, the historical-mix break-even is C / {eve.gp.mean():.6f} genuinely recovered evening baskets, before waste and other incremental costs. This is a contribution threshold, not a claim those baskets are recoverable. Obtain actual marginal labor costs and lost-order measurements. A simple queue/stockout logging pilot is lower cost than adding shifts blindly. Compare additional coverage with reassignment from quieter hours, respecting minimum service coverage.

## 2. Most growth comes from purchase frequency, not better basket economics

**Observed:** January averages {a.baskets_per_day:.2f} baskets/calendar day and ${a.gp_per_basket:.3f} GP/basket; June averages {b.baskets_per_day:.2f} and ${b.gp_per_basket:.3f}. GP/day increases from ${a.gp_per_day:.2f} to ${b.gp_per_day:.2f}. A symmetric two-factor decomposition assigns {share:.1%} of that increase to more baskets/day and {1-share:.1%} to GP/basket changes. The bridge is exact and splits the interaction equally. Calendar-day denominators account for unequal month lengths; equal-weekday averages are exported as a sensitivity.

**Decision:** do not call rising sales evidence that discounts or cross-selling improved order economics. Monitor GP/basket alongside baskets/day and capacity. 'More baskets' does not mean more unique customers or higher footfall: anonymous IDs, repeat visits and conversion prevent that interpretation. January and June are retrospective endpoints, not a causal pre/post experiment. Stable GP/basket does not mean a failed upsell program; no assignment data are available.

## 3. The naive basket-lift conclusion misses a useful target

**Observed:** Bakery + Matcha & Tea has raw training lift {selected.raw_lift_train:.2f}, which looks unpromising against independent basket presence. But most baskets have few lines; category presences compete for those limited slots. We compared pairs with 399 shuffled-label draws preserving every transaction's line count and category line frequencies within branch × month × order type × four-hour daypart. This asks whether a pair occurs more often than that basket-size/context baseline predicts.

January–April contains {int(selected.pair_baskets_train):,} Bakery+Matcha baskets versus {selected.expected_pairs_train:.1f} expected under this null: **{selected.conditional_enrichment_train:.2f}× enrichment**, BH-adjusted exploratory q={selected.enrichment_q_train:.4f} across all 36 category pairs. May–June has {int(selected.pair_baskets_replication):,} versus {selected.expected_pairs_replication:.1f}: **{selected.conditional_enrichment_replication:.2f}×**, q={selected.enrichment_q_replication:.4f}. Null ranges, all pairs and duplicate sensitivity are exported. The largest training enrichment is {top.category_a} + {top.category_b} ({top.conditional_enrichment_train:.2f}×); we retain the complete ranking, including failures. Matcha + bakery is an economically interpretable pilot candidate with large eligible volume, not a demonstrated optimum over every possible pairing.

**Interpretation:** the previous sparse product-pair search did not establish a strong product-specific bundle. Category-level preferences are more stable and support a focused experiment. The null assumes exchangeability of category labels within context; meal occasion, product availability and customer intent can still explain enrichment. Small q-values reject this specified shuffle baseline, not a causal no-cross-sell hypothesis. Both periods were inspected retrospectively; May–June is chronological replication, not an untouched prospective holdout.

**Financial gate:** there are {int(no_discount.eligible_a_only_baskets):,} matcha-category baskets without bakery and {int(no_discount.existing_pairs):,} existing paired baskets. At an assumed 3% *incremental* attachment of one bakery unit and unchanged historical bakery mix/contribution, a no-discount prompt yields **${no_discount.hypothetical_gp_before_expense:,.2f}** before implementation costs. Offering a 10% bakery rebate to new and existing pairs at the same adoption yields **${paid.hypothetical_gp_before_expense:,.2f}**, because existing purchases also receive the rebate. The rebate requires {paid.break_even_adoption:.1%} incremental adoption merely to break even before expenses. These are scenarios, not forecasts, and cannot be added to the Garden counterfactual without modeling overlaps. The target-unit GP already reflects historical discounts; an extra rebate is conservatively treated as incremental leakage.

**Decision:** test a no-discount bakery suggestion with matcha orders before buying attachment through blanket bundles. Randomize the prompt before the basket is finalized, with control, no-discount suggestion and rebate arms. Use contribution per assigned eligible order/customer including any substitution, incremental labor and non-completions. Train staff or use POS prompts consistently; log assignment, stockouts and completion. Reject if contribution after real costs does not improve. Attachments to categories other than bakery may compete, so measure whole-basket GP.

## 4. Promotions can look better simply because of the denominator

The preserved discount study already identifies a stronger mechanism than a routine dashboard: a larger basket is more likely to contain at least one discounted item. Fixed-basket label shuffling reproduces the observed 10% units gap. The 15% GP/basket comparison reverses when the baseline changes from network-wide to Harbour. Read ../analysis/outputs/REPORT.md for date-cluster intervals, context matching, overlap failures and the two campaign comparisons. None identifies a causal discount lift. Promotion decisions should use incremental contribution per assigned visitor, not GP among redeemers.

## Evidence and validation

- `tables/category_pair_null.csv`: all category pairs, both periods, raw lift, fixed-size null, enrichment and multiplicity-adjusted q.
- `tables/category_pair_duplicate_sensitivity.csv`: all-period duplicate-removal sensitivity; period differs from train/replication, so compare direction, not exact enrichment values.
- `tables/daypart_economics.csv`: all branches, demand and GP per nominal observed day-hour.
- `tables/growth_economics.csv`, `tables/growth_bridge.csv`: calendar and weekday-adjusted growth diagnostics.
- `tables/attachment_decisions.csv`: 1%, 3%, 5% assumed adoption with/without extra rebates, leakage and break-even.

Run `python scripts/deep_insights.py`. The data remain unchanged. Seeded permutation results are reproducible. All hypotheses are exploratory. Audit customer intent, category availability, queue behavior and supplier cash costs before implementing permanent changes.
'''
    text=text.replace('Calendar-day denominators account',f"A 1,999-draw circular seven-day block bootstrap gives a 95% interval of ${interval['low']:+.3f} to ${interval['high']:+.3f} for the June-minus-January GP/basket difference. This historical variability interval does not remove confounding or establish future stability. Calendar-day denominators account")
    (out/'deep_insights.md').write_text(text)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figures=out/'figures';figures.mkdir(exist_ok=True)
    best=pairs.head(4);positions=range(len(best));width=.35
    fig,ax=plt.subplots(figsize=(10,5))
    ax.bar([i-width/2 for i in positions],best.conditional_enrichment_train,width,label='Jan–Apr',color='#75543d')
    ax.bar([i+width/2 for i in positions],best.conditional_enrichment_replication,width,label='May–Jun',color='#b38b61')
    ax.axhline(1,color='#547965',linestyle='--',label='Basket-size/context null')
    ax.set_xticks(list(positions),best.category_a+' + '+best.category_b,rotation=15)
    ax.set(ylabel='Observed pair baskets / mean shuffled pair baskets',title='Category preferences hidden by naive lift · January–June 2026')
    ax.legend();fig.tight_layout();fig.savefig(figures/'category_enrichment.png',dpi=150);plt.close(fig)
    if verbose:print(text)
    return text

if __name__=='__main__':run()
