# Stories Coffee — executive recommendation

Garden's recorded gross margin is 46.91%, versus Harbour's 64.96%. Replacing Garden's costs with the same products' Harbour costs, holding quantities, prices and discounts fixed, raises six-month recorded gross profit by $15,923.47. Audit costing before changing procurement: the uniform ratios may reflect allocation rules rather than avoidable cash costs.

## Business problem
The file contains 51,177 item lines in 33,887 baskets, January 1–June 30, 2026. Revenue is $305,925.14; recorded gross profit is $179,430.49. Gross profit excludes payroll, rent and implementation costs.

## Evidence
- All 45 products are shared. Garden/Harbour cost ratios range from 1.4261 to 1.4386; price ratios range from 0.9512 to 0.9532.
- Product-branch cost values are constant: maximum distinct costs per product/branch is 1. This weakens a product-specific waste explanation; no transaction data identify the underlying costing rule.
- Iced Matcha contributes $827.28; the top five products account for 22.3% of the matched-cost difference. See `tables/matched_products.csv` for all products and `monthly_cost_gap.csv` for every month.
- Keeping every row yields $15,923.47; dropping excess exact duplicates as a sensitivity yields $15,887.50. Duplicates are retained in the baseline because no line identifier establishes erroneous duplication.
- A separate discount investigation finds that classifying baskets by any discounted line can create apparent basket-size uplift even under shuffled labels. See the existing `analysis/outputs/REPORT.md`; do not treat basket differences as causal effects.

## Competing explanations
Product mix, price and discount differences are evaluated by exact Shapley attribution of GP/unit, averaging all 24 factor orderings. See `tables/decomposition.csv` and `common_mix.csv`. These explain arithmetic differences, not causal mechanisms. Supplier contracts, recipes and accounting allocations remain unresolved. Fixed costs across all dates/products favor investigating a systematic rule first.

## Proposed solution
Finance should trace the highest-dollar products from POS cost masters through recipes and supplier invoices. Compare Garden and Harbour on identical SKUs, portions, freight, waste and allocation definitions. Confirm avoidable cash expense before procurement changes. Preserve quality and service during any pilot.

## Financial impact
At 25%, 50%, 75% and 100% recoverability, hypothetical six-month GP gains are $3,980.87, $7,961.74, $11,942.60 and $15,923.47. Net benefit subtracts an unknown implementation expense E. Reject an intervention if verified avoidable benefit does not exceed E and operational risk. If the difference is purely allocation, cash savings may be zero.

Exact per-product Harbour price alignment adds $4,985.91 before demand response at unchanged discounts and mix. Its proportional volume-loss break-even is 9.63%, before implementation costs. Demand elasticity is unknown. Do nothing is preferable to an untested chain-wide price change; a targeted costing audit is the lower-commitment alternative.

## Risks and limitations
36.5% of baskets have no customer ID. Observed repeat customers are a selected subset. 132 excess duplicate rows remain unresolved. Revenue has 0 deviations beyond half a cent and GP has 0; see the quality report. Source rounding is preserved. Six historical months do not establish future performance, cash savings or treatment effects. Scenarios are assumptions, not forecasts.

## Proposed pilot
Audit the top five dollar contributors first. If invoices confirm a recoverable difference, compare eligible products under current and revised procurement/recipe practices, with matched control products and pre-period trends. Finance must set duration and minimum worthwhile cash benefit after estimating day-level variance and serial correlation. Stop for quality, stockout or service deterioration. For promotions, randomize 0%, 10%, 15% offers before purchase, log nonbuyers, and measure incremental contribution per assigned visitor. Sample size requires a specified minimum effect and pre-pilot visitor-level variance.

## Final decision
Authorize a costing audit; authorize operational changes only after avoidable cash costs and quality safeguards are verified. Hold broad discount expansion pending a randomized test. Avoid blanket bundle discounts: co-purchase is not proof of incremental demand.

## Additional discovery
The top five products explain 22.3% of the recorded cost gap. The largest contributor is Iced Matcha. This audit ranking is supplemented by category-pair null models, evening demand exposure and growth-quality investigations in deep_insights.md. These exploratory findings support experiments, not claims of measured intervention benefits.

## Basket investigation
Strongest training lift among pairs with at least 30 training baskets: Cinnamon Roll + Strawberry Matcha; train n=38, lift=1.09; test n=27, lift=1.13. Small lifts and sparse pair support do not justify blanket bundle discounts. Pair selection uses training lift; the later data are for descriptive validation only.

Average units/basket: 1.596; GP/basket: $5.29. List-price concessions total $2,179.36; this is mechanical arithmetic, not lost causal profit.

## Evidence index
- `tables/duplicate_sensitivity.csv`
- `tables/branches.csv`
- `tables/monthly.csv`
- `tables/products.csv`
- `tables/categories.csv`
- `tables/order_types.csv`
- `tables/matched_products.csv`
- `tables/decomposition.csv`
- `tables/common_mix.csv`
- `tables/cost_scenarios.csv`
- `tables/monthly_cost_gap.csv`
- `tables/associations.csv`
- `tables/bundle_scenarios.csv`
- `tables/discounts.csv`
- `tables/basket_distribution.csv`
- `tables/customer_summary.csv`
- `tables/column_types.csv`
- `tables/weekday.csv`
- `tables/hour.csv`
- `tables/external_effects_baskets.csv`
- `tables/external_effects_revenue.csv`
- `tables/external_holdout.csv`
- `tables/drink_mix_by_temperature.csv`
- `tables/month_turn_placebo.csv`
- `tables/rain_dine_in.csv`
- `tables/external_daily_panel.csv`
- `tables/clock_template_check.csv`
- `tables/hour_regimes.csv`
- `tables/hourly_profile.csv`
- `tables/staffing_template.csv`
- `tables/feature_effects.csv`
- `tables/feature_catalog.csv`

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


# Causal decision chains — protect contribution, customers and service

**The recommendation is conditional:** first validate Garden's cash costs; then test prices or attachment only where whole-basket contribution and service stay healthy. More revenue, higher item margin and larger baskets can each coexist with worse business outcomes.

This document separates **observations**, **accounting identities**, and **hypothesized causal links**. The transaction file identifies arithmetic and associations, not the effects of changing prices, suppliers, staffing or offers. All arrows below are proposed mechanisms until tested. A small p-value for co-purchase does not validate an intervention chain.

## 1. A cost-allocation problem can trigger the wrong operational response

**Hypothesis chain:** branch costing rule → lower recorded Garden GP → management pressure → cheaper supplier or recipe change → possible quality/availability change → possible lost repeat purchases → chain contribution.

**What is observed:** product-branch unit costs never change in the six months; Garden's same-product costs are about 43% above Harbour's. The $15,923.47 recorded difference is real arithmetic. Whether it represents actual avoidable cash costs is unknown.

**Fork in the chain:** if costs are allocations, changing vendors might not remove the expense at all. If invoices confirm a real procurement disadvantage, savings may be available, but lower quality, waste, freight and stockouts can consume them. Neither pathway is established by the CSV.

**Financial gate:** assuming 50% cash recovery, unchanged mix and proportional customer loss, Garden's $7,961.74 hypothetical saving survives at most 14.5% volume loss before expenses. That is a break-even ceiling, not an acceptable service target. A quality failure can be unacceptable before a financial threshold is reached. If a subjective probability p of real savings is used to value an audit, p × recoverable difference − audit cost is only an assumption-based screening calculation, not measured ROI.

**Protect Stories:** finance reconciles costs to invoices and the cost master first. Procurement compares landed cost per conforming unit, waste and reliability. Operations validates recipes and portions. Reject operational change if savings are allocation-only or specifications fail. Do not penalize a branch manager for an unverified accounting rule.

## 2. Raising a cheap item's margin can put an expensive basket at risk

**Hypothesis chain:** price increase → contribution per retained item rises → customer either drops/substitutes that item OR abandons the purchase → other products' contribution is lost → chain-wide net result.

**New measured exposure:** Garden Sparkling Water contributes $269.85 GP, but all Garden baskets containing it contribute $917.51. Its Harbour-price alignment adds only $46.75 at unchanged sales. An item-only calculation tolerates 14.8% lost item sales; a whole-basket exit pathway tolerates just **4.85%** of those baskets. The latter is not a prediction; it is a different behavioral assumption.

For Iced Matcha the corresponding thresholds are 9.5% item loss versus **6.3%** complete-basket loss. All 45 products are exported. Product scenarios overlap, so never sum their containing-basket exposure or individual counterfactuals.

**Accounting identity:** U is the price uplift with all current purchases retained; P is current target-item GP; B is GP of all containing baskets. Under representative proportional losses, item-only break-even = U/(P+U), while complete-basket break-even = U/(B+U). Source discounts, costs and remaining product mix are fixed. Real substitution, unequal customer responses or cross-branch recapture change the result.

**Protect Stories:** price-test only with a simultaneous control, stable pre-purchase assignment and visitor/nonbuyer logging. Measure full baskets, alternative products, complaints and other-branch contribution. A Garden win caused solely by moving a Harbour purchase is not a chain win. Customer-ID missingness limits linkage; log assignment and identification coverage explicitly. Reject a change that raises item margin while reducing contribution per eligible visitor after costs.

## 3. A successful upsell can still reduce total evening profit

**Hypothesis chain:** prompt → extra pastry → extra service work → possible longer queue → possible abandoned orders or missed service standards → whole-basket losses offset attachment GP.

**Observed target:** 2,861 evening matcha baskets lack bakery. **Assumed response:** a no-discount prompt causes one extra bakery unit in 3% of those baskets. At historical evening bakery contribution, the replay adds **$212.29**, before labor, waste or substitution. Incremental adoption is unknown.

**New loss budget:** historical evening GP/basket is $5.34. The modeled attachment benefit is erased by **39.7** representative evening baskets lost across the six-month scope. With 40 lost baskets, the net is **$-1.44** before program costs. This does not claim 40 baskets will be lost. It shows how little queue damage this particular assumed uptake can absorb.

**Protect Stories:** compare randomized prompt/no-prompt blocks within comparable branch/daypart exposure; log preparation and checkout times, arrival and completion counts, stockouts, waste and marginal labor. Individual-order randomization can miss harm to other customers sharing the queue. Set block length and washout using measured queue-clearance times; retain all arrivals and completions, not only customers accepting the prompt. Use inference clustered at the assignment block and account for repeated dates. The main outcome is total contribution per assigned service block, not AOV among successful orders. Set acceptable wait/quality thresholds before the test; stop at an operational breach even if average order value rises. Do not convert the loss budget into allowable extra seconds without actual service-time and arrival-rate data.

## 4. Discounts can pay for demand that was already coming

**Hypothesis chain:** offer → lower contribution on existing demand + possible conversion/extra units → product substitution, purchase timing shifts or branch switching → later retention → incremental chain contribution.

**Observed warning:** any-discount baskets mechanically overrepresent larger baskets; fixed-basket shuffled labels reproduce the observed 10% units gap. The 15% GP comparison reverses against Harbour's own baseline. Neither result proves offers are harmful; both show why a selected redeemer comparison is inadequate.

**Protect Stories:** randomize offer eligibility before purchase and include nonbuyers. Analyze contribution per assigned visitor after program and marginal operating costs, plus total chain contribution and repeat behavior over a pre-specified follow-up. Account for product and branch displacement; do not call a moved purchase incremental. Do not add historical discount concessions to claimed cost savings. Existing 0/10/15% campaign estimates and their limitations remain in ../analysis/outputs/REPORT.md.

## 5. Traffic growth can hide a worsening operational business

**Hypothesis chain:** basket volume grows → workload rises → possible extra labor/waste/capacity expense → service and conversion change → operating contribution may diverge from recorded gross profit.

The observed GP/day bridge assigns about 99.2% of January–June growth to more baskets/day; GP/basket changes little. Evening activity is financially important, but no queue, labor or capacity records exist. Therefore the file cannot show that demand exceeded capacity, that staffing is inefficient, or that net profit rose with GP.

**Protect Stories:** obtain actual labor and waste costs and instrument arrivals/completions. Compare adding coverage, moving existing coverage within minimum service constraints, and doing nothing. Use incremental contribution after costs and service quality; do not infer an optimal roster from hourly sales alone.

## 6. A loyalty campaign can improve the metric without improving retention

**Hypothesis chain:** campaign changes willingness to give an ID → a larger share of repeat visits is recognized → observed repeat rate rises → management mistakenly credits retention → budget allocated without incremental contribution.

Around 36.5% of source baskets lack customer IDs. We cannot observe the true repeat rate of anonymous purchasers or estimate a campaign effect from this file. A changing identification mechanism is a plausible bias, not a discovered event.

**Protect Stories:** report identification and attrition by assigned arm, keep assignment independent of later purchases, and include zero-purchase outcomes. Require contribution improvement and sensitivity to unmatched identities before funding expansion. Never call a rise in recognized repeat customers proof of loyalty improvement.

## Decision sequence and stop rules

1. **Verify cash accounting before operational pressure.** No supplier changes justified by an allocation-only difference.
2. **Instrument service before stimulating peak demand.** No staffing or queue effect is inferred from transactions alone.
3. **Test suggestions before rebates.** Any incremental attachment must survive lost-basket, substitution and operating-cost budgets.
4. **Price-test whole baskets, not isolated margins.** Track visitor outcomes and possible chain displacement.
5. **Scale only on incremental contribution and customer/service guardrails.** Pre-register the minimum worthwhile benefit, spending cap, acceptable quality/wait/complaint limits, duration and analysis. These thresholds must come from Stories; they are not fabricated here.

The data support a map of decisions and failure pathways, not a proven causal network. Further evidence could reverse any intervention recommendation. Tables provide reproducible monetary gates and all product exposures; no commercial pilot has been performed.
