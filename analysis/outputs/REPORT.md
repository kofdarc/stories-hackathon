# Do Stories’ discounts grow baskets or gross profit?

Decision brief for 17 October 2026. Evidence: 2026-01-01 through 2026-06-30, USD.

## Recommendation for today’s hackathon

**Do not expand either discount on the strength of discounted-basket averages. Keep 10% expansion on hold and test 15% against 10% and no offer at Harbour before repeating it at scale.** Baskets containing a 10% line but no 15% line average +0.238 units and $+0.17 gross profit versus baskets with no discounted lines. For 15%, the differences are +0.189 units and $+0.37. Larger baskets have more opportunities to contain a discounted line: shuffled labels reproduce the observed 10% units gap. The 15% GP association reverses against Harbour’s own no-discount baseline (-0.33 dollars/basket). The adjusted daily GP differences during the two 15% windows are negative with wide intervals. These associations do not establish incremental profit or prove that removing existing offers would improve it.

## Measured results: simple baseline

Unit of analysis: one transaction ID, with all its lines summed. `0%` means every line is undiscounted. `10%` means at least one 10% line and no 15% line; `15%` is defined symmetrically and can include undiscounted lines. `both` is reported separately. A blanket 10% or 15% basket discount is **not** observed here. Basket size is units and line count; AOV is revenue after discounts. List value is quantity × supplied unit price, before discount. Gross profit is the supplied revenue minus product costs, subject to source rounding; it excludes payroll, rent and program costs.

| group | n | units | lines | revenue | gp | list_value | gross_margin |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0% | 30640 | 1.574 | 1.489 | 8.966 | 5.275 | 8.966 | 0.588 |
| 10% | 2789 | 1.812 | 1.715 | 9.667 | 5.449 | 10.276 | 0.564 |
| 15% | 442 | 1.762 | 1.649 | 9.142 | 5.645 | 10.178 | 0.618 |
| both | 16 | 2.375 | 2.250 | 12.343 | 7.729 | 13.828 | 0.626 |

Compared with the no-discount baseline, 10% units are 15.2% higher and GP/basket 3.3% higher; 15% units are 12.0% higher and GP/basket 7.0% higher. Neither comparison measures added visits, conversion, or customer retention.

## Challenge the first explanation

1. **Basket exposure creates selection.** We shuffled 10% labels among non-15% item lines within branch × month × category, holding every basket and its outcomes fixed (400 draws, seed 490). Baskets with any shuffled discount still show a units gap. This diagnostic makes no claim that actual labels were randomly assigned. Its simulated GP/revenue gaps retain recorded financial outcomes and are not a financial counterfactual or causal p-value.

| outcome | observed_10pct_difference | shuffled_median | shuffled_low | shuffled_high |
| --- | --- | --- | --- | --- |
| units | 0.238 | 0.249 | 0.219 | 0.277 |
| lines | 0.225 | 0.236 | 0.210 | 0.260 |
| revenue | 0.701 | 1.379 | 1.184 | 1.564 |
| gp | 0.175 | 0.832 | 0.723 | 0.935 |
| list_value | 1.309 | 1.385 | 1.195 | 1.574 |

2. **Context and customer selection.** Standardization compares treated and untreated orders in the same branch, month, weekday, four-hour daypart, order type and customer-ID availability, weighting cells by their treated counts (minimum three treated and five controls). Adjusted 10% units: +0.231 (95% interval +0.189 to +0.273); GP: +0.154 (95% interval -0.018 to +0.326). This detailed match retains only 49.4% of 10% baskets and does not generalize to all discounted purchases. A coarse branch/month/type/ID-availability match retains all 10% baskets and is also reported. Same identified-customer comparison uses customers who purchased both with and without 10%, and still cannot remove time-varying intent or targeting. It is a sensitivity check, not customer randomization.

3. **Product mix and line quantity.** Item-line comparisons control for product and context. They answer whether discounted lines contain more units, not whether orders contain extra lines. Matching on products or existing eligible baskets can condition on purchase decisions affected by the offer, so these are mechanism diagnostics only.

| comparison | difference | low | high | treated | coverage |
| --- | --- | --- | --- | --- | --- |
| 10% line product/time matched | 0.000 | -0.009 | 0.010 | 2812 | 0.983 |
| 15% line product/time matched | unavailable | unavailable | unavailable | 0 | 0.000 |

4. **15% geography and timing.** All 504 15% lines occur at Harbour in Cold Coffee or Desserts, 12–19 March and 12–19 May inclusive. There are 458 orders with any 15%, including 16 also carrying 10%. A national 0%-basket baseline mixes branch, timing, category choice and eligibility. Harbour’s own no-discount baskets average $5.97 GP, versus $5.65 for 15% baskets: the apparent network-wide positive association reverses within branch, even before time/product adjustments. Every eligible-category line during those Harbour dates is 15% discounted. Restricting to Harbour, campaign dates and baskets containing eligible categories (excluding any 10%) gives units unavailable (no treated/control overlap); GP unavailable (no treated/control overlap). Eligibility rules and offer exposure are inferred from purchased items; we have no record of who saw or qualified for the offer.

All order contrasts and retained-sample coverage:

| comparison | outcome | difference | low | high | treated | controls | coverage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10% unadjusted | units | 0.238 | 0.211 | 0.266 | 2789 | 30640 | 1.000 |
| 10% unadjusted | gp | 0.175 | 0.063 | 0.286 | 2789 | 30640 | 1.000 |
| 15% unadjusted | units | 0.189 | 0.135 | 0.243 | 442 | 30640 | 1.000 |
| 15% unadjusted | gp | 0.371 | 0.187 | 0.554 | 442 | 30640 | 1.000 |
| 10% coarse context matched | units | 0.238 | 0.211 | 0.266 | 2789 | 30640 | 1.000 |
| 10% coarse context matched | gp | 0.159 | 0.052 | 0.265 | 2789 | 30640 | 1.000 |
| 10% context matched | units | 0.231 | 0.189 | 0.273 | 1377 | 9775 | 0.494 |
| 10% context matched | gp | 0.154 | -0.018 | 0.326 | 1377 | 9775 | 0.494 |
| 10% same identified customer | units | 0.259 | 0.216 | 0.301 | 1753 | 7629 | 0.994 |
| 10% same identified customer | gp | 0.247 | 0.076 | 0.417 | 1753 | 7629 | 0.994 |
| 15% Harbour eligible same dates | units | unavailable | unavailable | unavailable | 0 | 0 | 0.000 |
| 15% Harbour eligible same dates | gp | unavailable | unavailable | unavailable | 0 | 0 | 0.000 |
| 10% duplicate sensitivity | units | 0.240 | 0.213 | 0.268 | 2789 | 30640 | 1.000 |
| 10% duplicate sensitivity | gp | 0.182 | 0.071 | 0.294 | 2789 | 30640 | 1.000 |
| 15% duplicate sensitivity | units | 0.188 | 0.135 | 0.242 | 442 | 30640 | 1.000 |
| 15% duplicate sensitivity | gp | 0.371 | 0.186 | 0.557 | 442 | 30640 | 1.000 |

Intervals are approximate 95% normal sandwich intervals clustered by calendar date, conditional on selected matching cells and observed target weights. Same-customer intervals do not additionally cluster by customer; repeat-customer dependence may make them too narrow. They quantify sampling variability, not uncertainty from confounding. No multiplicity correction; interpret as exploratory.

## 15% daily campaign comparison and temporal replication

Compare each inferred eight-day campaign with its preceding 28 days. The simple baseline is Harbour’s raw daily pre/during change. The adjusted comparison subtracts contemporaneous changes at Garden/Uptown, using OLS with branch and date fixed effects and branch-specific weekday effects. Treatment is Harbour × campaign dates. Outcomes include **all** Harbour purchases to capture category substitution and basket attachment. Eligible-category and other-category comparisons, plus branch linear trend sensitivity, appear in `campaign_daily_comparisons.csv`. Category order counts overlap and must not be added together.

| window | outcome | raw_harbour_change | pre_harbour_mean | difference | low | high |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-03-12 | units | 2.804 | 130.821 | 3.239 | -12.746 | 19.224 |
| 2026-03-12 | orders | 3.161 | 81.464 | 3.342 | -3.725 | 10.410 |
| 2026-03-12 | gp | -10.151 | 486.901 | -6.852 | -75.284 | 61.580 |
| 2026-05-12 | units | 12.554 | 154.321 | -2.446 | -18.441 | 13.549 |
| 2026-05-12 | orders | 6.357 | 96.393 | -2.685 | -12.006 | 6.637 |
| 2026-05-12 | gp | 22.584 | 579.717 | -25.881 | -88.904 | 37.141 |

GP sensitivity checks (daily dollars):

| scope | window | window_type | branch_trend | difference | low | high |
| --- | --- | --- | --- | --- | --- | --- |
| all | 2026-03-12 | campaign | False | -6.852 | -75.284 | 61.580 |
| all | 2026-03-12 | campaign | True | -66.671 | -164.086 | 30.744 |
| all | 2026-05-12 | campaign | False | -25.881 | -88.904 | 37.141 |
| all | 2026-05-12 | campaign | True | -64.628 | -164.975 | 35.719 |
| all | 2026-02-26 | pre-period placebo | False | 1.604 | -59.094 | 62.302 |
| all | 2026-04-28 | pre-period placebo | False | 75.979 | -24.315 | 176.273 |
| eligible | 2026-03-12 | campaign | False | -16.511 | -36.729 | 3.707 |
| eligible | 2026-03-12 | campaign | True | -35.964 | -68.987 | -2.940 |
| eligible | 2026-05-12 | campaign | False | -31.334 | -56.733 | -5.934 |
| eligible | 2026-05-12 | campaign | True | -40.472 | -90.580 | 9.637 |
| other | 2026-03-12 | campaign | False | 9.659 | -46.634 | 65.952 |
| other | 2026-03-12 | campaign | True | -30.707 | -111.556 | 50.141 |
| other | 2026-05-12 | campaign | False | 5.452 | -46.094 | 56.999 |
| other | 2026-05-12 | campaign | True | -24.156 | -104.273 | 55.961 |

Pre-period placebos move the eight-day window 14 days earlier and use their own preceding 28 days, with no 15% campaign in those fitting windows. They diagnose whether this design generates apparent changes before the offer. Wide placebo intervals cannot establish parallel trends. Eligible-category GP declines must be weighed against any gains elsewhere; scope `other` captures the latter without counting the discounted categories.

Differences are per branch-day. Intervals use date-cluster covariance with finite-sample correction and normal critical values (36 date clusters per window). They do not account for dependence across dates and may understate uncertainty under serial correlation. Common date effects absorb network-wide weather/seasonality but not Harbour-specific events, marketing, staffing or tourism. Linear trends extrapolate pre-period trends and can also absorb true effects. Only three branches and two short episodes sharply limit inference. Parallel counterfactual trends and no cross-branch spillovers are assumptions, not established facts.

March is the exploratory episode; May is a chronological replication under the same specified comparison. Both episodes were visible during this retrospective analysis, so May is **not** an untouched prospective holdout. This is an explanatory study, not a trained forecasting or targeting model; no predictive accuracy claim is made. We compare every adjusted daily result with the raw Harbour baseline rather than presenting complexity as evidence. An independently randomized test is needed for validation.

## Recorded discount accounting versus estimated business value

The recorded list-price concession is **$2,178.09**: $1,706.54 on 10% lines and $471.55 on 15% lines. This is arithmetic (list value minus recorded revenue), **not recoverable savings**: removing the offer could lose sales. Total recorded GP is $179,430.49, not incremental profit attributable to discounts.

The following estimates are explicitly hypothetical. For 10%, use the observed undiscounted mix across the network; for 15%, use undiscounted Harbour eligible-item mix in the 28 days before March. Assume constant unit prices, unit costs and mix, all 1,000 baseline units receive the discount, additional units cost the same, and no displacement or visit effects elsewhere. These are item-volume scenarios, not a replay of current partially discounted baskets. Estimated contribution subtracts an assumed $100 program cost per 1,000 baseline units. Labor capacity, waste and fixed costs remain unpriced.

Formula: ΔGP = 1,000 × [(1 + assumed unit lift) × (price × (1 − discount) − unit cost) − (price − unit cost)]. Break-even unit lift before program costs = discount / (reference gross margin − discount).

| rate | assumed_unit_lift | reference_margin | break_even_unit_lift | incremental_gp_before_program_cost | assumed_program_cost | incremental_contribution_after_program_cost |
| --- | --- | --- | --- | --- | --- | --- |
| 0.10 | 0.00 | 0.59 | 0.20 | -569.84 | 100 | -669.84 |
| 0.10 | 0.10 | 0.59 | 0.20 | -291.38 | 100 | -391.38 |
| 0.10 | 0.20 | 0.59 | 0.20 | -12.92 | 100 | -112.92 |
| 0.10 | 0.30 | 0.59 | 0.20 | 265.54 | 100 | 165.54 |
| 0.10 | 0.40 | 0.59 | 0.20 | 544.00 | 100 | 444.00 |
| 0.15 | 0.00 | 0.66 | 0.29 | -877.65 | 100 | -977.65 |
| 0.15 | 0.10 | 0.66 | 0.29 | -578.22 | 100 | -678.22 |
| 0.15 | 0.20 | 0.66 | 0.29 | -278.80 | 100 | -378.80 |
| 0.15 | 0.30 | 0.66 | 0.29 | 20.62 | 100 | -79.38 |
| 0.15 | 0.40 | 0.66 | 0.29 | 320.04 | 100 | 220.04 |

No annualized savings or ROI is claimed. The needed causal unit lift may differ from an observed basket gap and depends heavily on cannibalization, discount eligibility, product mix and labor costs. A higher measured GP/basket alone is insufficient if profit per eligible visitor or per day falls.

## Data quality, provenance and limitations

- 51,177 lines aggregate to 33,887 orders, $305,925.14 revenue and $179,430.49 GP. All 181 dates appear at each of three branches. Source SHA-256: `f1672e728c28295b2b802d878fd38a158ba039827b429355e8438ee0463237a1`. Raw CSV is never overwritten. No external sources are required; all empirical claims trace to this CSV.
- 132 exact repeated excess rows ($741.43 revenue) are retained because identical items may be valid purchases. Dropping exact repeats and reaggregating is a sensitivity check in the contrasts table, not an asserted cleaning correction.
- 1,950 orders contain multiple distinct line rates. The four exposure groups prevent treating them as uniform whole-basket discounts. Four orders have all three rates; 16 have both nonzero rates.
- Customer IDs are missing on 12,353 orders (36.5%). Identified-customer evidence is selected and does not generalize to anonymous customers.
- 0 inconsistent within-order metadata; 0 missing required cells; 0 revenue and 0 GP arithmetic errors beyond one cent. One-cent rounding differences: 478 revenue and 0 GP lines. Quantity is positive, discount rates are 0/10/15%, and 0 lines have negative GP. Checks do not independently verify supplier costs, tax treatment, omitted refunds, or completeness versus the POS ledger.
- All transaction IDs start `SYN-`. The brief says IDs are replacements; the prefix alone does not establish that purchases are synthetic. Validate provenance with Stories before a live decision. Timezone, offer assignment, marketing spend, eligible nonbuyers, footfall, stockouts, staffing and external events are absent. No October transactions are available, so this is historical evidence for today’s recommendation, not current trading performance.

## Practical next step

Run a concurrent randomized 0%/10%/15% offer test at Harbour on cold coffee/desserts, assigning before purchase and logging all assigned visitors, including nonbuyers. Use stable customer assignment where possible, otherwise documented randomized time blocks with washout and no overlapping offers. Compare **gross contribution per assigned visitor**, net of product, incremental labor and program costs, with total daily GP as a guardrail. Track conversion, units, net revenue, category substitution, repeat visits, complaints and stockouts. Stratify by weekday/daypart; use intention-to-treat and cluster inference at the randomization unit. Pre-register the minimum worthwhile profit gain, power calculation, stopping rule and budget before launch. March/May contrasts are insufficient to choose a precise causal effect size for powering the test. A successful 15% test must beat both no-offer and 10% on net contribution, not just units.

We rejected a basket-level propensity score or flexible uplift model: purchased products, basket size and discount presence can be post-offer variables, and assignment/eligibility are missing. More predictive complexity cannot recover the missing counterfactual. We also rejected scaling the crude GP/basket gap by all transactions as “business value.”
