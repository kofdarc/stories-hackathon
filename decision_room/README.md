# Stories recommendations

**Upload a sales CSV → get six plain-language recommendations.**

The app automatically reviews opening hours, which branches warrant a closure review, restocking/preparation, waste, price increases/decreases, and two-item combos with branch/time suggestions. Every section says what to do, why, and what to check next. Supporting numbers are collapsed by default. Reports can be downloaded as a standalone HTML file.

## Run

From the repository root, using the existing project environment:

```sh
.venv/bin/python -m decision_room.server
```

Open **http://127.0.0.1:8765**. Choose your CSV, drag it onto the upload area, or use the existing Stories CSV if present. No slider setup, scenario configuration or API-key entry is required. A column template is available on the upload page. Uploads must use the original transaction columns, be UTF-8, and be smaller than 40 MB. Extra columns are reported as unused rather than silently treated as inventory or accounting inputs.

The server can start without a bundled transaction file. Uploaded data is processed in memory; the browser session retains only the aggregate report. Raw uploaded files are not saved by the server. The app serves only its explicit public assets, not repository files.

## Gemini configuration

The app automatically loads `decision_room/.env`. This local file contains `GEMINI_API_KEY`, is excluded from Git, and has owner-only filesystem permissions. An existing process environment value takes precedence. `GEMINI_MODEL` optionally selects an account-accessible model; otherwise the server discovers a supported Flash model. Use `.env.example` as a blank template on another machine.

Gemini powers optional follow-up explanations after a report is generated. The six recommendations and all supporting arithmetic work without Gemini. Follow-ups send the question and aggregate report to Google, never source transaction rows or customer identifiers. The API key stays on the server and is not included in browser responses or downloads.

## What the recommendations mean

- **Opening hours:** reviews the quieter opening/closing edge hour for each branch and shows the avoidable operating cost needed to justify removing it. It cannot identify a financially optimal schedule without actual operating costs and customer displacement measurements.
- **Branch closure:** compares recorded branch gross profit and identifies a review priority. It does not recommend a permanent closure from sales alone; payroll, rent, exit costs and customer migration are missing.
- **Restocking:** lists recent daily sales and observed variation for the fastest-selling items. These are preparation guides, not inventory order quantities. On-hand stock, lead times, shelf life and stockouts are unknown.
- **Waste:** flags slower-selling fresh-category items to inspect. It does not label unsold stock as measured waste or invent waste savings.
- **Prices:** calculates the volume-loss limit for a 5% increase and extra volume required for a 5% cut, assuming unchanged mix, discounts and unit costs. Customer response remains unmeasured.
- **Combos:** finds pairs present in both earlier and later sales in the same branch/time window. It suggests a full-price pairing test before a rebate. Co-purchases do not establish incremental offer demand or optimal timing. Popular items can dominate the counts.

All money is USD. Gross profit subtracts recorded product costs, not rent, payroll or other overhead. Historical time coverage is inferred from sales; zero-sale days can also mean missing data or closures. Data quality notes, source dates and calculation assumptions accompany every report. Unknown operating inputs remain unknown.

## Verify

```sh
.venv/bin/python -m unittest discover -s decision_room/tests -v
node --check decision_room/static/app.js
```

The 24 tests cover CSV validation and upload without a bundled source/key; all six report sections; price-change break-even gates; combo replication/time windows; no invented closure or waste savings; aggregate-only exports; and the underlying scenario arithmetic and HTTP boundaries. Legacy calculation APIs remain available for development but are not exposed in the simplified business interface.
