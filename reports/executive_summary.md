# Stories Coffee — executive recommendation

Garden's recorded gross margin is 46.91%, versus Harbour's 64.96%. Replacing Garden's costs with the same products' Harbour costs, holding quantities, prices and discounts fixed, raises six-month recorded gross profit by $15,923.47. Audit costing before changing procurement: the uniform ratios may reflect allocation rules rather than avoidable cash costs.

## Top 5 actions
1. **Audit Garden's costs.** $15.9K of six-month gross profit depends on whether Garden's costs, about 43% above Harbour's for identical products, are avoidable.
2. **Staff and prep for the evening peak.** 19:00–23:59 earns 44.6% of gross profit (see deep_insights.md).
3. **Suggest a bakery item with matcha, with no discount.** The pair is bought together 1.7× more often than chance; a rebate would turn the gain into a loss.
4. **Hold blanket discounts.** Run a randomized 0/10/15% test first.
5. **Ignore the weather when planning.** Demand follows the clock, not the temperature.

No product needs to be cut. The weakest, Sparkling Water, still earns 0.74% of gross profit, and the bottom products are staples that mostly sell in multi-item baskets. Review recipe and waste costs for Sparkling Water (45% margin), Granola Yoghurt (53% margin), Soup of the Day (56% margin).

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

## Further decision evidence
See [deeper investigations](deep_insights.md) for evening demand exposure, an exact growth-quality bridge, and category-pair preferences tested against a basket-size/context baseline. These support focused service and no-discount attachment experiments; they do not establish causal savings.

## Protecting the business before rollout
The [causal decision brief](causal_decisions.md) traces accounting, procurement quality, whole-basket pricing, queue/attachment, promotion displacement and customer-identification risks. It calculates the losses each scenario can absorb and specifies measurements and stop rules for unresolved links.
