<div align="center">

# Stories · Business Recommendations

**Upload a CSV. Get six clear recommendations, charts and answers.**

**Live app: [Open Stories Recommendations](https://stories-decision-room.onrender.com/)**

</div>

## What the app does

Upload your sales CSV and receive a plain-language report covering:

| Decision | What you receive |
| --- | --- |
| Opening hours | Quieter opening/closing hours to review by branch, with the cost saving needed to justify a change |
| Branch closure | Branch profit comparison and what must be checked before deciding to close |
| Restocking | Recent sales quantities to guide preparation, by branch and item |
| Waste | Slower-selling fresh items to review for smaller batches; no invented waste savings |
| Prices | Break-even sales changes for a 5% increase and a 5% decrease |
| Combos | Specific two-item pairs and branch/time windows to test, with evidence from earlier and later sales |

Each recommendation includes **what to do, why, a next step, and a Python-generated chart**. Supporting numbers are available without cluttering the main report. Download the report as a self-contained HTML file.

**Recommendations change with the uploaded dataset.** Branches, products, schedules, quantities, pairings, charts and price thresholds are recomputed from that CSV. The app does not return a fixed list of Stories recommendations. The 5% price scenarios, combo observation thresholds and time-window definitions are fixed analytical choices; their results vary with the data.

Sales alone cannot reveal rent, payroll, inventory on hand, expiry, waste or how customers will respond to a new offer. The app identifies review priorities and small tests, and states what information is missing. Gross profit is sales minus recorded product costs, before operating expenses. No prospective commercial pilot has validated these recommendations.

## Data processing and the math

**CSV → validation → sales summaries → decision rules → Python charts → optional LLM explanation.** Pandas handles the data; Matplotlib draws the charts. The uploaded-data report is calculated before any question is sent to a language model.

We check the required columns, dates, numeric values, positive whole-number quantities, discounts between 0 and 1, and consistent order details. We also reconcile each line: `revenue = quantity × unit price × (1 − discount)` and `gross profit = revenue − quantity × unit cost`, allowing approximately half a cent for rounding. Invalid files are rejected. Extra columns are reported as unused; duplicate-looking rows are flagged and retained because they may be legitimate purchases.

We derive hour, weekday and other time fields, and group item lines into **baskets by transaction ID** so an order containing three products counts as one order. Recent calculations use the latest **56 calendar days**, or the available period if shorter. Daily averages include dates with no recorded sales; the CSV cannot distinguish missing records from actual closures.

| Decision | Calculation in the current app |
| --- | --- |
| Hours | Sum recent gross profit by branch and hour, then divide by calendar days. Compare each branch’s first and last observed sales hours and flag the weaker edge. Shortening hours only helps when **avoidable operating costs saved exceed gross profit lost**, adjusted for customers returning later. |
| Branch review | Compare full-period gross profit, **gross profit ÷ calendar days**, and **gross profit ÷ revenue**. The lowest-gross-profit branch is a review priority; closure needs operating costs and customer-transfer estimates. |
| Restocking | Calculate daily units per branch/item, including zero-sale dates. Show the three fastest sellers per branch, their mean, and the **25th–75th percentile** range. These are preparation guides; stock and supplier lead times are still needed for order quantities. |
| Waste | Identify fresh-food candidates from category names and rank their average daily sales from lowest upward. Actual discarded quantities and expiry times are needed to measure waste. |
| Prices | Let `G` be recent gross profit and `R` revenue. For a **5% increase**, maximum proportional volume loss is `1 − G / (G + 0.05R)`. For a **5% decrease**, extra volume required is `G / (G − 0.05R) − 1`, when margins permit. Both assume unchanged mix, discounts and unit costs. |
| Combos | Count distinct two-product pairs within baskets by branch and morning/afternoon/evening window. Split dates roughly **70% earlier / 30% later**; require at least **5 earlier and 3 later** pair baskets. Rank by the smaller of those counts, breaking ties by their total. Repetition supports a pilot, not proof that a discount causes extra sales. |

## Where ML fits

**The current recommendation engine uses descriptive statistics and explicit business rules.** It does not train a demand forecast, price-elasticity model or inventory optimizer on an upload. Combo analysis is co-purchase counting with a later-period recurrence check, rather than a trained recommender or causal validation.

The ML component is the **pretrained Gemini language model**, with optional DeepSeek fallback, used for natural-language follow-ups as described below. Its weights are not trained or fine-tuned on the uploaded CSV. Python supplies calculated report facts; the model helps interpret questions and explain them simply.

The original Stories findings at the bottom also reference earlier forecasting checks and **Monte Carlo simulations**. Monte Carlo repeatedly evaluates assumed customer responses and savings to show a range of possible outcomes; it does not learn those responses from sales. Those historical experiments are separate from the current upload-to-report calculations and are not rerun for every CSV.

## Our NLP approach

The language assistant helps business stakeholders understand the calculated report:

1. **Natural-language input:** the stakeholder types a question, or clicks **Ask about this recommendation**.
2. **Grounding:** Python supplies the current report's calculated facts and assumptions. Charts, raw transaction rows and customer IDs are excluded from model context.
3. **Interpretation and explanation:** Gemini interprets the question and explains the relevant findings in ordinary business language. Recent follow-ups provide conversation context.
4. **Fallback:** if Gemini fails, the server tries DeepSeek when `DEEPSEEK_API_KEY` is configured. The interface identifies the provider that answered.
5. **Evidence boundary:** the assistant is instructed to avoid inventing missing inputs, treatment effects or new numerical scenarios. Financial calculations and chart generation remain in Python.

This is report-grounded prompting, not model fine-tuning, a trained intent classifier, semantic search or a causal model. LLM explanations can still make mistakes; inspect the supplied calculations before a business decision.

## Run

Requires Python 3.12 or newer.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m decision_room.server
```

Open [the local app](http://127.0.0.1:8765). Upload the authorized CSV; no database is required. The page provides a CSV header template and accepts files under 40 MB. Dates use `YYYY-MM-DD`, times `HH:MM:SS`, and money is USD.

## Server configuration

Set these in the server environment, or copy `decision_room/.env.example` to the ignored `decision_room/.env`:

```dotenv
GEMINI_API_KEY=your_key
DEEPSEEK_API_KEY=your_optional_backup_key
```

`GEMINI_MODEL` and `DEEPSEEK_MODEL` are optional. Gemini uses a model discovered from the account; DeepSeek defaults to `deepseek-flash`. A Gemini key cannot authenticate to DeepSeek. Without provider keys, the calculated recommendations and charts still work.

The Gemini key has been stored as the repository's encrypted `GEMINI_API_KEY` Actions secret. **GitHub Actions secrets do not automatically become Render environment variables.** The Gemini key is also configured in the Render app’s server environment. No credential is committed or embedded in the browser.

For your Render setup, the build command is `pip install -r requirements.txt` and the start command is `python -m decision_room.server`. The app reads `PORT`, binds publicly when `RENDER` is set, and recognizes `RENDER_EXTERNAL_URL`. The production app is linked at the top of this README.

## Verify

```sh
.venv/bin/python -m unittest discover -s decision_room/tests -p test_submission.py -v
node --check decision_room/static/app.js
```

Portable tests cover all six recommendation layers, charts, changes across datasets, CSV validation, aggregate-only language-model context and provider fallback. Provider fallback is tested with mocked failures; live DeepSeek verification requires its separate key.

## Submission contents

Only the CSV recommendation app, its minimal Python helpers, frontend, requirements, CI checks and portable tests are submitted. No raw dataset, database, key, notebook, slide deck or old dashboard is included in the current source tree.

Uploads are processed in server memory and are not saved as raw files. Aggregate reports remain in the browser session's server memory until eviction or restart. Follow-ups share aggregate report facts with the configured provider. A single-process server is intended for this prototype; durable multi-instance sessions, access controls and stronger abuse limits would be needed for a larger public service.

**Team:** John Kofdarelli · Marc Zeeny

## Our recommendations for the original Stories dataset

These are our findings for **January–June 2026**, covering **51,177 item lines, 33,887 baskets, $305,925.14 revenue and $179,430.49 recorded gross profit**. They are reference recommendations for this dataset, not a fixed answer returned for every upload.

| Move | Our recommendation | Why and what to test |
| --- | --- | --- |
| **1 · Check Garden’s costs** | Audit costing before changing suppliers. | The same 45 products have recorded costs about **43% higher** at Garden than Harbour. Replacing them with Harbour’s costs at Garden’s quantities creates a **$15,923.47 six-month gross-profit difference**. At 25–100% recoverability, that is roughly **$4K–$16K** before implementation expense. Trace invoices and recipes first: if this is an accounting allocation, cash savings could be **$0**. |
| **2 · Plan by the clock** | Prepare staff, ice, desserts and seating for the evening peak. | **19:00–23:59 generates 44.6% of recorded gross profit**; the 21:00 hour contains **4,273 baskets**, versus **724 at 07:00** over the six months. Weather/calendar additions did not improve the existing May–June forecasting check. Prioritize the clock pattern; confirm the cost of any extra shift coverage. |
| **3 · Test discounts in quieter periods** | Test moving offers away from the busiest hours; do not expand 15% campaigns without evidence. | About **52% of discounted item lines** occur in the evening. This does not prove those customers would buy without the offer. Compare no offer, 10% and 15% in comparable periods, including nonbuyers, and measure total contribution after discount costs. |
| **4 · Ask “want a pastry?”** | Test a full-price evening pastry suggestion before adding a rebate. | Bakery attachment is a plausible opportunity, but co-purchase is not proof that an offer creates extra demand. Under the original **3% extra matcha-to-bakery attachment assumption**, the historical six-month replay adds about **$393 before extra costs**; a **10% rebate**, including existing paired purchases, changes that scenario to about **−$497**. Stop if queue, labor or substitution costs erase the gain. |
| **5 · Test a 5% price rise** | Start at one branch with a comparison group and watch whole-basket profit. | The earlier chain-wide simulation gives a median **$7,305 six-month gross-profit gain**, with P5–P95 **$3,025–$11,128**, across **20,000 assumed-response draws**. These are conditional scenarios, not measured price-response effects or a one-branch forecast. Recalculate the break-even loss for the selected branch and stop if observed demand/retention losses erase the benefit. |
| **6 · Test opening later** | After verifying removable roster hours, test **Uptown at 09:00** and **Garden at 08:00**. | The earlier three-hour closure simulation gives median savings of **$656 over 182 days**, P5–P95 **−$807 to +$2,315**, and a positive result in **75.2% of assumed futures**. Actual wage savings and customers returning later determine the outcome. No saved roster hours may mean no benefit. |
| **7 · Hold unsupported promotions** | Do not roll out blanket bundles, late-evening clearance or seasonal promotions from these patterns alone. | Busy evenings are not automatically clearance periods. Six months do not establish annual seasonality, and co-purchase does not establish discount uplift. Test incremental contribution and collect actual expiry/waste records before treating markdowns as waste reduction. |

**These are proposed audits and pilots, not proven commercial gains.** Preserve quality and service, compare with doing nothing, and scale only when measured contribution after additional costs improves. The app’s current calculations may differ from these historical reference scenarios because its windows, inputs and methods are explicitly stated in each uploaded-data report.
