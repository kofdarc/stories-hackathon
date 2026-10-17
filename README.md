<div align="center">

# Stories · Business Recommendations

**Upload a CSV. Get six clear recommendations, charts and answers.**

**Live app: Render production URL pending your deployment.**

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

The Gemini key has been stored as the repository's encrypted `GEMINI_API_KEY` Actions secret. **GitHub Actions secrets do not automatically become Render environment variables.** Set the key in Render's server environment as well. No credential is committed or embedded in the browser.

For your Render setup, the build command is `pip install -r requirements.txt` and the start command is `python -m decision_room.server`. The app reads `PORT`, binds publicly when `RENDER` is set, and recognizes `RENDER_EXTERNAL_URL`. Replace the production-link line at the top with your actual Render URL after deploying. No deployment was performed as part of this submission cleanup.

## Verify

```sh
.venv/bin/python -m unittest discover -s decision_room/tests -p test_submission.py -v
node --check decision_room/static/app.js
```

Portable tests cover all six recommendation layers, charts, changes across datasets, CSV validation, aggregate-only language-model context and provider fallback. Provider fallback is tested with mocked failures; live DeepSeek verification requires its separate key.

## Submission contents

Only the CSV recommendation app, its minimal Python helpers, frontend, requirements, CI checks and portable tests are submitted. No raw dataset, database, key, notebook, slide deck or old dashboard is included in the current source tree.

Uploads are processed in server memory and are not saved as raw files. Aggregate reports remain in the browser session's server memory until eviction or restart. Follow-ups share aggregate report facts with the configured provider. A single-process server is intended for this prototype; durable multi-instance sessions, access controls and stronger abuse limits would be needed for a larger public service.

**Team:** John Kofdarelli. , MARC ZEENY
