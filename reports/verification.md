# Verification — 17 October 2026

Causal decision additions: five tests check complete-basket price exposure, exact item-versus-basket break-even identities, attachment loss/cost/substitution subtraction, procurement gate reconciliation and invalid/zero assumptions. Scenario tables expose all 45 products; the decision register labels observed and unidentified links separately. The dashboard adds Causal Decision Chains and surfaces the quantified downside gates on Executive Overview.

Added deep-insight validation: the suite now traverses the Deep Decision Insights page alongside the existing pages. Five additional tests verify that label shuffling cannot create pairs in one-line baskets, observed pair counts and seeds are correct, the growth bridge reconciles exactly, rebate leakage and break-even equations agree, and day-block uncertainty is reproducible. The 399-draw category null was run for Jan–Apr, May–Jun and duplicate sensitivity; the 1,999-draw seven-day block bootstrap was executed. `figures/category_enrichment.png` was visually inspected. Existing Weather & Calendar work is preserved.

Story: managers choose a scope or financial assumption in Streamlit → the server selects authorized CSV rows → independent Python functions aggregate or simulate them → the browser displays recalculated evidence.

| Boundary | Evidence |
|---|---|
| CSV → validation | Analysis executed on 51,177 lines / 33,887 baskets; source hash in data_quality.json; no half-cent financial exceptions or metadata conflicts |
| Analytics → evidence | Full pipeline generated CSVs, charts, CEO report and detailed report; matched gap independently verified against quantity-weighted source costs |
| Controls → scope | AppTest traversed all six pages and changed branch, category, order type and dates, confirming totals change and no rendering exceptions |
| Assumptions → financial response | AppTest changed cost recovery and confirmed scenario net benefit changes; unit checks verify unchanged baseline, full demand loss and exact break-even |
| Server → browser | Streamlit started at 127.0.0.1:8501; browser accessibility state showed $305,925.14 revenue, $179,430.49 GP and $15,923.47 matched-cost difference; screenshot in figures/dashboard_executive.png |
| Reference reconstruction | Both screenshots visually inspected; monthly line, weekday bars, hour bars, category bars and synchronized branch filter implemented; invalid two-byte workbook documented |
| Existing discount analysis | Full 400-permutation pipeline rerun to /tmp/stories-integrated-discounts; all reconciliation assertions passed; contrasts numeric maximum difference versus saved evidence: 0.0; four existing tests passed |
| Existing standalone simulator | Node model checks passed: known scenarios, 100 component/branch reconciliations, deterministic paired trials and timeline |
| Scientific plots | Priority-product and Shapley figures visually inspected; dollars, denominator and dates labeled |

Run `python -m unittest discover -s tests -v` for the new suite. Tests cover grain reconciliation, matched costs, scope/missing matches, exact Shapley addition, price lookup alignment, scenario boundaries, quality, README synchronization and dashboard interactions. Use `python -m unittest discover -s analysis -v` for the four preserved discount tests, and `node simulator/tests/model.cjs` for browser-model arithmetic.

Limitations: screenshots capture the narrow Codex browser panel; Excel-native behavior is not tested or delivered. The reference offers no usable workbook internals. No controlled commercial pilot has occurred. No public push or deployment occurred. The pre-existing Git checkout still tracks raw/derived transaction data; the source-only submission archive excludes those records and Git history.
