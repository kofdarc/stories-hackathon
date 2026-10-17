<div align="center">

# Stories Coffee

### Seven simple moves. Real results decide.

A decision guide for Garden, Harbour and Uptown · EECE 490 Hackathon

[The seven moves](#seven-moves-at-a-glance) · [Try the tools](#try-the-tools) · [Evidence](#follow-the-evidence) · [Setup guide](../reports/project_guide.md#how-to-run)

</div>

**Start with Garden’s recorded costs. Then test changes in the shop.** The same products carry about 43% higher unit costs in Garden’s books than in Harbour’s. That deserves an invoice audit before a supplier change. Evening demand, quiet-hour offers, pastry prompts, prices and opening hours each suggest a focused next step.

This README follows the plain-language story of the [seven-move presentation](../reports/Stories_Recommendations_ELI5.pptx), with claims checked against the calculations. **No commercial pilot has been performed.**

## The business in one view

| January 1–June 30, 2026 | All three branches combined |
| :--- | ---: |
| Calendar days in the extract | 181 |
| Baskets / purchases | 33,887 |
| Item lines | 51,177 |
| Revenue after discounts | $305,925.14 |
| Recorded gross profit | $179,430.49 |
| Products shared by all branches | 45 |

A basket can contain several item lines. **Gross profit (GP) means revenue minus recorded product costs.** It excludes payroll, rent and other operating expenses. Throughout this page, contribution after costs also subtracts the extra costs of the proposed action. [Source reconciliation](../reports/data_quality.json)

## Seven moves at a glance

| Move | Why it deserves attention | Next step |
| :--- | :--- | :--- |
| **1. Check Garden’s costs** | $15,923.47 matched-cost difference over the observed six months | Trace the cost master to invoices |
| **2. Plan by the clock** | 19:00–23:59 earned 44.6% of recorded chain GP | Match preparation and coverage to branch/hour patterns |
| **3. Test offers in quiet times** | Existing discount comparisons cannot identify added demand | Randomize offers before purchase |
| **4. Ask “want a pastry?”** | Cold Coffee + Bakery co-purchase repeats in both time periods | Test an evening prompt at full price |
| **5. Test a 5% price rise** | Modeled chain GP gain: median $7,305 over six months | Start at one branch with concurrent controls |
| **6. Test opening later** | Modeled saving: median $656 over 182 days for three early branch-hours | Confirm removable staff hours first |
| **7. Leave unsupported promotions on hold** | Six months cannot establish seasonal demand or promotion effects | Require evidence of incremental contribution |

**How to read the numbers:** observed results describe the supplied file. Modeled results replay assumptions. Pilot effects are still unknown. The scenarios overlap and must not be added into a “total opportunity.”

## 1 · Check Garden’s costs

Garden’s recorded gross margin is **46.91%**, compared with **64.96%** at Harbour. All 45 products appear in both branches. Their Garden/Harbour unit-cost ratios run from 1.4261 to 1.4386, and each product/branch cost stays fixed throughout the extract.

![Recorded gross margin by branch, January–June 2026: Garden about 47%, Harbour 65%, Uptown 63%](../reports/figures/branch_margin.png)

At Garden’s actual quantities, replacing its recorded costs with Harbour’s adds **$15,923.47** to historical GP, holding prices, discounts and sales fixed. Recovering 25–100% of that gap means **$3,980.87–$15,923.47 before implementation costs**. An allocation-only difference could produce **$0 cash savings**.

**Try:** audit the five largest dollar contributors, beginning with Iced Matcha. Compare identical products, recipes, portions, freight and invoices. **Stop:** reject a procurement change if the gap is accounting-only, or if verified savings fail to cover its costs without harming quality or availability.

[Matched products](../reports/tables/matched_products.csv) · [Recovery scenarios](../reports/tables/cost_scenarios.csv) · [Audit and validation plan](../reports/experiment_plan.md)

## 2 · Plan by the clock

The **21:00–21:59 hour contains 4,273 baskets**, versus **724 at 07:00–07:59**, summed across all three branches and all 181 days. Evening hours, 19:00–23:59, contribute **44.6% of total recorded GP**. This is an aggregate pattern, not a claim that every day has the same rush.

**Try:** use the branch × hour × weekday template to plan ice, bakery preparation, seating and coverage. Log arrivals, completed orders and queue times before adding staff. **Stop:** revise the change if extra contribution does not cover added labor/waste, or if service deteriorates.

Weather and calendar features did not improve the May–June demand forecast in the repository’s holdout check. Daily rain, temperature, holiday and Ramadan estimates have intervals that include zero. That supports using the clock as the starting point here; it does **not** establish that weather never matters at Stories.

[Hourly totals](../reports/tables/hour.csv) · [Planning template](../reports/tables/staffing_template.csv) · [Weather evidence and limits](../reports/external_factors.md)

## 3 · Test discounts when the shop is quiet

Quiet mornings are a **test candidate**. We do not know which evening customers would have bought without an offer. Discounted baskets tend to be larger, but larger baskets also have more chances to contain a discounted line. Shuffled labels reproduce the observed 10% basket-size gap. The 15% campaign estimates remain inconclusive, with wide uncertainty.

**Try:** at Harbour, randomize no offer, 10% and 15% eligibility before purchase within comparable weekday/daypart groups. Give quiet periods a prespecified analysis, keep a budget cap, and include visitors who buy nothing. Measure contribution per assigned visitor after program and marginal operating costs. **Stop:** do not expand an offer unless it beats the agreed minimum worthwhile gain and service guardrails. An inconclusive result does not justify rollout.

A four-week window can be an initial operational check. Final duration and sample size require visitor-level variance and a chosen minimum effect. A simple before/after comparison cannot settle the question.

[Discount investigation](../analysis/outputs/REPORT.md) · [Randomization, power and stopping rules](../reports/experiment_plan.md)

## 4 · Ask “want a pastry?” in the evening

Offer a bakery item with cold coffee at full price. Cold Coffee + Bakery appears **1.18×** as often as the context/basket-size null predicts in January–April and **1.23×** in May–June. That makes the pairing worth testing. It does not measure the response to a staff prompt.

The slide’s “66% margin” refers approximately to **Cold Coffee’s recorded category margin (66.1%)**. Bakery’s is **60.1%**. Neither is an incremental-profit guarantee: a pastry still costs ingredients and can add labor, waste or queue pressure.

**Try:** randomize prompt/no-prompt service blocks during 19:00–23:59, with enough washout for queues to clear. Count all arrivals and completions. **Stop:** pause for a wait-time or quality breach, or if total contribution per block falls after costs. In a separate evening *matcha* example, assumed 3% bakery attachment adds only $212.29 over six historical months before costs; about 40 representative lost evening baskets erase it. That is a warning about queue harm, not a cold-coffee forecast.

[Pairing evidence](../reports/tables/category_pair_null.csv) · [Category margins](../reports/tables/categories.csv) · [Queue and lost-basket checks](../reports/causal_decisions.md#3-a-successful-upsell-can-still-reduce-total-evening-profit)

## 5 · Test a 5% price rise at one branch

A $4.00 item becomes $4.20. The repository’s simulation gives a **$7,305 median GP gain**, with a **$3,025–$11,128 P5–P95 range**, for a 5% increase on every item **across all three branches over the historical six-month sales base**. Those dollars are not a prediction for one pilot branch, and do not include a full operating-cost model.

**Try:** refresh invoice costs, then test +5% at one branch against the other two, checking pre-period comparability. Keep price-ending experiments separate so their effects remain interpretable. Measure full-basket contribution, units, visitors, complaints and purchases shifting between branches. Four weeks is a proposed initial check, subject to adequate precision.

**Stop:** roll back if contribution after costs falls or service/customer guardrails fail. At the observed chain margin, a uniform 5% rise breaks even at roughly **7.9% proportional volume loss**, assuming unchanged discounts, costs and mix. This is a screening ceiling, not a universal 8% baskets/day rule. Branch margins and lost-basket composition change it.

[Simulation results and inputs](../reports/monte_carlo.md) · [Whole-basket price risks](../reports/causal_decisions.md#2-raising-a-cheap-items-margin-can-put-an-expensive-basket-at-risk)

## 6 · Open later where early demand is thin

Uptown’s 07:00 hour averages **$4.37 recorded GP per calendar day**. The repository’s base staffing/energy scenario puts that hour at **$6.53 of operating cost**. The cost is assumed, not a measured payroll or electricity bill. With one staff member and lower energy use, closing can lose money.

**Try:** verify the roster and opening tasks, then pilot Uptown opening at 09:00 and Garden at 08:00, with Harbour retaining its schedule. Track full-day contribution and whether early customers return later. **Stop:** restore hours if realized savings fail to cover lost contribution, including later purchases and costs of the change. Staff needed for baking or deliveries may eliminate the expected labor saving.

The combined three-hour simulation pays in **75.2% of draws**: median **$656**, P5–P95 **−$807 to +$2,315**, over an assumed **182-day horizon**. These are outcomes under selected assumptions, not measured odds of success.

[Branch-hour economics](../reports/tables/outside_hour_economics.csv) · [Simulation summary](../reports/tables/mc_summary.csv)

<details>
<summary><strong>What drives the simulations?</strong></summary>

Both use **20,000 draws, seed 490**. P5–P95 is the middle 90% of simulated outcomes, not a confidence interval for an actual intervention.

- **Opening hours:** 1 or 2 early-shift staff (40%/60% assumed probabilities), triangular wage $1.80/$2.60/$3.50 per staff-hour, 50–100% of staff hours removable, 1.5/3/5 kWh per open hour, generator share 60–100%, and generator tariff $0.45–$0.59/kWh. Customer recapture follows Beta(2,3), averaging 40%. Hourly GP is bootstrapped across 181 calendar days, with demand between the H1 average and June run-rate.
- **Pricing:** constant-elasticity demand, category elasticity triangular −1.5/−0.8/−0.25, with a 1–1.5× multiplier for coffee. Cost-drift assumptions also vary. All saved +5% draws are positive, but that reflects the model and chosen inputs. Permanent customer loss, real substitution and service effects remain unproven.

Replace assumptions with branch records before committing. The external wage/energy inputs are documented scenario inputs, not independently verified current quotes in this README. [Full inputs](../reports/tables/mc_inputs.csv) · [Executable model](../scripts/monte_carlo.py)

</details>

## 7 · Skip promotions the evidence cannot support yet

| Idea | What the file supports |
| :--- | :--- |
| End-of-day discounts | Late evening is busy in aggregate. Test incrementality before subsidizing that demand. |
| Winter or holiday campaigns | Six months cannot separate annual seasonality from trend. Holiday null estimates do not prove zero effect. |
| A summer iced-drink push | Cold drinks remain about 60% **of drink units** in this extract. Validate the source before using that stability as a real-world rule. |
| Blanket bundle discounts | Co-purchase is association. A rebate can reduce contribution on existing pairs without creating enough new purchases. |

## Try the tools

**Streamlit dashboard:** explore branch sales, recorded profitability, causal decision checks, forecasts and scenario controls. Supply the authorized CSV locally, then run from the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

The dependency pins were tested with **Python 3.14**. Place `stories_transactions.csv` at the repository root. Open [the local dashboard](http://127.0.0.1:8501). [Full setup, rebuild commands and architecture](../reports/project_guide.md#how-to-run)

**Decision notebook:** [Stories Coffee Decision Lab](../colab_recommendations/Stories_Coffee_Decision_Lab.ipynb) is a present, self-contained notebook for hours, closure, preparation, markdowns, loyalty, prices, discounts, combos and delivery scenarios. Open it in Google Colab, run the setup, and upload only a CSV you are authorized to process there. It ships without executed outputs; a live Colab run is not verified by this README. Hosted upload requires your own data-sharing permission.

**Feature notebook:** [Feature effects](../notebooks/feature_effects.ipynb) contains the existing feature investigation and saved outputs. Treat transaction-derived variables and associations according to their documented limits.

The separate local text decision app is still in development and is not a verified deliverable here.

## Follow the evidence

| For… | Read… |
| :--- | :--- |
| Calculations and alternative explanations | [Methodology](../reports/methodology.md), [full analysis](../reports/full_analysis.md), [assumptions](../reports/assumptions_and_limitations.md) |
| Pilot design and business risks | [Experiment plan](../reports/experiment_plan.md), [causal decision chains](../reports/causal_decisions.md) |
| Time patterns and pairing diagnostics | [Deep investigations](../reports/deep_insights.md), [feature loop](../reports/feature_loop.md) |
| Simulation uncertainty | [Monte Carlo report](../reports/monte_carlo.md), [saved results](../reports/tables/mc_summary.csv) |
| Conditional sales forecasts | [Backtests and forecast limitations](../reports/forecasting.md) |
| Setup, project structure and prior checks | [Preserved project guide](../reports/project_guide.md), [verification record](../reports/verification.md) |

Some earlier reports use stronger shorthand than the evidence warrants. This README states the qualified interpretation. Forecasts depend on the historical trend continuing; validate POS totals against settlements and costs against invoices before using them for commitments.

## Data, attribution and sharing

About **36.5% of baskets lack customer IDs**. The baseline retains **132 excess duplicate-looking rows**, since no unique line identifier establishes that they are errors. Costs and prices are fixed within product/branch throughout the file. These patterns warrant source validation. Invoices, waste, labor, nonbuyer conversion and actual elasticity are unavailable. Six historical months do not establish future performance or causal savings.

**Do not publish this checkout as-is.** Raw CSVs and database/SQL exports were already tracked. `.gitignore` does not remove tracked records or Git history. Nothing was pushed or published for this README work. Obtain sharing permission or prepare a separate clean source-only repository. The [packaging guide](../reports/project_guide.md#limitations-and-publication-status) describes the existing allowlisted archive; its current packager excludes the newer `colab_recommendations/` and `decision_room/` directories. Review notebook outputs and every aggregate before redistribution.

**Reference credit:** [Abel Atangs’ coffee-shop-analytics](https://github.com/atangsabel13/coffee-shop-analytics), inspected at commit `2b044959782783c2ab542657a84d6e45c359dc4f`, informed the dashboard organization and chart concepts. Its two-byte workbook supplied no usable formulas or PivotTables. Stories calculations and implementation are original to this project. [Full attribution and reuse audit](../reports/reference_implementation.md)

**Team:** contributor names have not been supplied. Add the actual team before submission.
