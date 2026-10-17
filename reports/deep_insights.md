# Stories Coffee — deeper decision insights

The practical opportunity is to **protect evening service and test targeted, no-discount attachment**, while finance audits Garden's recorded costs. Sales growth alone does not show better basket economics. Conventional association-rule lift can also miss pair preferences because the typical basket is small. These are measured diagnostics and proposed experiments, not measured treatment benefits.

## 1. A coffee business with an evening service risk

**Observed:** 19:00–23:59 accounts for 14,981 baskets (44.2%) and $80,044.80 recorded GP (44.6%). 07:00–10:59 contributes 4,777 baskets (14.1%) and $24,530.64 GP. The five evening hours handle 2.51 times as many baskets per nominal clock-hour as the four morning hours. All branches show this pattern; see daypart_economics.csv. These periods are explicit clock-hour bins, not inferred opening hours.

**Why this changes a decision:** copying the reference shop's morning-heavy staffing narrative would misallocate attention. Inspect queues, stockouts and labor deployment around the evening peak before adding morning promotions or cutting late coverage. The file does not contain staffing, waiting times, capacity or missed customers, so it cannot establish understaffing or recommend headcount cuts.

**Financial gate:** evening GP per observed basket is $5.34. For an incremental staffing cost C, the historical-mix break-even is C / 5.343088 genuinely recovered evening baskets, before waste and other incremental costs. This is a contribution threshold, not a claim those baskets are recoverable. Obtain actual marginal labor costs and lost-order measurements. A simple queue/stockout logging pilot is lower cost than adding shifts blindly. Compare additional coverage with reassignment from quieter hours, respecting minimum service coverage.

## 2. Most growth comes from purchase frequency, not better basket economics

**Observed:** January averages 146.61 baskets/calendar day and $5.305 GP/basket; June averages 230.20 and $5.325. GP/day increases from $777.80 to $1225.83. A symmetric two-factor decomposition assigns 99.2% of that increase to more baskets/day and 0.8% to GP/basket changes. The bridge is exact and splits the interaction equally. A 1,999-draw circular seven-day block bootstrap gives a 95% interval of $-0.067 to $+0.113 for the June-minus-January GP/basket difference. This historical variability interval does not remove confounding or establish future stability. Calendar-day denominators account for unequal month lengths; equal-weekday averages are exported as a sensitivity.

**Decision:** do not call rising sales evidence that discounts or cross-selling improved order economics. Monitor GP/basket alongside baskets/day and capacity. 'More baskets' does not mean more unique customers or higher footfall: anonymous IDs, repeat visits and conversion prevent that interpretation. January and June are retrospective endpoints, not a causal pre/post experiment. Stable GP/basket does not mean a failed upsell program; no assignment data are available.

## 3. The naive basket-lift conclusion misses a useful target

**Observed:** Bakery + Matcha & Tea has raw training lift 0.89, which looks unpromising against independent basket presence. But most baskets have few lines; category presences compete for those limited slots. We compared pairs with 399 shuffled-label draws preserving every transaction's line count and category line frequencies within branch × month × order type × four-hour daypart. This asks whether a pair occurs more often than that basket-size/context baseline predicts.

January–April contains 1,234 Bakery+Matcha baskets versus 699.7 expected under this null: **1.76× enrichment**, BH-adjusted exploratory q=0.0180 across all 36 category pairs. May–June has 760 versus 441.3: **1.72×**, q=0.0180. Null ranges, all pairs and duplicate sensitivity are exported. The largest training enrichment is Cold Drinks + Meals (1.87×); we retain the complete ranking, including failures. Matcha + bakery is an economically interpretable pilot candidate with large eligible volume, not a demonstrated optimum over every possible pairing.

**Interpretation:** the previous sparse product-pair search did not establish a strong product-specific bundle. Category-level preferences are more stable and support a focused experiment. The null assumes exchangeability of category labels within context; meal occasion, product availability and customer intent can still explain enrichment. Small q-values reject this specified shuffle baseline, not a causal no-cross-sell hypothesis. Both periods were inspected retrospectively; May–June is chronological replication, not an untouched prospective holdout.

**Financial gate:** there are 5,299 matcha-category baskets without bakery and 1,994 existing paired baskets. At an assumed 3% *incremental* attachment of one bakery unit and unchanged historical bakery mix/contribution, a no-discount prompt yields **$393.09** before implementation costs. Offering a 10% bakery rebate to new and existing pairs at the same adoption yields **$-496.97**, because existing purchases also receive the rebate. The rebate requires 7.6% incremental adoption merely to break even before expenses. These are scenarios, not forecasts, and cannot be added to the Garden counterfactual without modeling overlaps. The target-unit GP already reflects historical discounts; an extra rebate is conservatively treated as incremental leakage.

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
