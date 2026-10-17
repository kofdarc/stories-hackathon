# Stories Coffee — Colab decision lab

Open **[Stories_Coffee_Decision_Lab.ipynb](Stories_Coffee_Decision_Lab.ipynb)** in [Google Colab](https://colab.research.google.com/) using **File → Upload notebook**, then **Runtime → Run all**. Confirm authorization and upload the original transaction CSV using the panel at the bottom. No repository checkout, LLM key, support-module upload or Drive mount is needed. In local Jupyter, enter an authorized CSV path instead.

The notebook covers all nine decision layers:

| Layer | Decision and financial gate |
|---|---|
| Hours | Later opening, earlier/later closing, extension demand, avoidable hourly cash costs and recaptured contribution |
| Permanent closure | Source contribution lost, avoidable fixed costs, full exit cost, customer migration, destination capacity/displacement and recurring payback |
| Restock/preparation | Product sales forecast, current-policy comparison, on-hand/lead-period order target, overage/shortage costs and service quantile |
| Waste/expiry | Markdown sell-through versus organic sales, sunk acquisition costs, disposal/salvage, regular-demand cannibalization and discount leakage |
| Loyalty | Identified cohort, descriptive mature 30-day return, induced visits, organic reward leakage and displaced visits |
| Price increases | Unit contribution versus all containing-basket exposure, staged item loss, substitution and whole-basket abandonment |
| Discounted items | Branch/time targeting, replacing existing concessions, incremental demand, substitution and queue/basket losses |
| Two-item combos | Which A+B, branch/daypart, train/holdout co-purchase support, explicit pair price, existing-pair leakage and break-even adoption |
| Delivery offers | Timing and basket-mix proxy, assumed demand, commission, packaging/courier/fees, channel switching and capacity losses |

Choose a common horizon, branch and calibration window; expand the relevant assumption controls and recalculate. Inspect rankings, formulas, charts and the separate do-nothing option. Use **Find combo branch/time candidates**, **Draw break-even sensitivities** and **Download aggregate report ZIP** as needed. Reports always recalculate current controls to avoid exporting stale results.

All intervention response parameters are assumptions. Unknown fixed cash savings, demand uplift, migration and extra visits start at zero. Initial inventory purchases and displaced delivery contribution use **explicitly labeled sales proxies**, not inventory or delivery observations. Positive value qualifies a hypothesis for a pilot. Overlapping scenarios must not be added. Current inventory policy is an editable counterfactual, so the restock delta is a policy-to-policy simulation rather than an identified improvement over actual operations.

The default 56-day calibration window uses recent rates rather than treating six months as a stable forecast. Change the window to inspect drift. Branch dates without records are zero sales under an explicit exposure assumption. The original CSV has no delivery orders, staffing, operating calendar, actual inventory/waste, expiry, lease/exit terms, campaign assignment or elasticity. A historical sales forecast cannot establish latent demand during stockouts. Finished-item preparation quantities cannot be converted to ingredient purchases without recipe/yield data.

## Data handling

The `.ipynb` is self-contained, output-free and includes no raw transaction rows or customer IDs. The user supplies their own authorized CSV; only the original 14 columns are read. Exact repeated rows can be retained or removed. Schema, metadata conflicts, types, ranges and financial reconciliation are checked. The UI blocks financial decisions if reconciliation fails.

No LLM API calls, data publishing or automatic Drive upload occur. Colab is hosted by Google; use an account and environment approved for this data. Clear all outputs before sharing an executed notebook. The optional ZIP contains aggregates, assumptions, forecast scores and pair summaries; inspect it before sharing.

## Local verification and maintenance

From the repository root, using a Python environment containing pandas/numpy:

```bash
python -m unittest discover -s colab_recommendations/tests -v
```

For notebook/UI verification, install the dependencies in `colab_recommendations/requirements.txt`, then:

```bash
python colab_recommendations/build_notebook.py
python colab_recommendations/verify_notebook.py /authorized/path/stories_transactions.csv
```

`engine.py` is the tested source; `build_notebook.py` embeds it verbatim in the notebook. Rebuild after editing either the engine or UI generator. `verify_notebook.py` validates the notebook schema, executes its actual code cells, constructs real ipywidgets, exercises the authorization gate, branch controls, calculations, candidate explorer, nine sensitivity curves and report ZIP/download callback. It scans all exports for source transaction and customer IDs and verifies a failed upload clears stale results. It saves only aggregate verification metadata and a chart in `verification/`.

The test run is local; hosted Colab's browser upload/download dialogs are not automated. The setup uses normal `%pip` and Google Colab APIs with a local-Jupyter fallback. No hosted Google account was accessed.

The original EECE490 brief drives the business reasoning, baselines, costs, alternatives and validation. No course slides were supplied or assumed. All project changes for this deliverable are confined to `colab_recommendations/`.
