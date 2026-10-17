# Discount analysis

Start with the [business recommendation](outputs/BUSINESS_RECOMMENDATION.md), then the [full report](outputs/REPORT.md). These are generated from the source CSV by `run_analysis.py`; the original CSV, database and existing simulator are untouched.

## Reproduce

From the repository root, use Python 3.10+ (verified with the version recorded in `outputs/quality_and_provenance.json`):

```sh
python3 -m venv /tmp/stories-discount-venv
/tmp/stories-discount-venv/bin/python -m pip install -r analysis/requirements.txt
OPENBLAS_NUM_THREADS=1 /tmp/stories-discount-venv/bin/python analysis/run_analysis.py
/tmp/stories-discount-venv/bin/python -m unittest discover -s analysis -v
```

No network, API keys or database are used after installing the two dependencies. Results are committed for inspection without an installation. The script takes about 20 seconds locally. All 400 label-shuffle draws use seed 490. No timestamps are injected into outputs; library/Python versions and source SHA-256 are recorded. Small numerical differences across linear algebra implementations are possible.

To verify a rerun without overwriting the committed outputs:

```sh
OPENBLAS_NUM_THREADS=1 /tmp/stories-discount-venv/bin/python analysis/run_analysis.py --output /tmp/stories-discount-rebuild
diff -r analysis/outputs /tmp/stories-discount-rebuild
```

Use the same pinned packages and Python version for a byte-for-byte comparison; otherwise the provenance file will differ. `--permutations` can change the number of diagnostic draws (minimum 20). The campaign windows and written interpretation are specific to the supplied January–June 2026 source snapshot; using a different `--source` requires reviewing the report's fixed context and campaign definitions.

## Inspect the evidence

| Output | What it supports |
| --- | --- |
| `basket_summary.csv` | Unadjusted no-discount baseline, explicit mixed-rate groups, units, AOV, GP and gross margin |
| `branch_summary.csv`, `monthly_summary.csv` | Geography, time and basket mix alternatives |
| `contrasts.csv` | Raw and matched order differences, date-cluster intervals, overlap/coverage and duplicate sensitivity |
| `line_contrasts.csv` | Product/time matched item quantity and financial differences; unavailable comparisons remain blank |
| `selection_placebo.csv`, `selection_placebo_summary.csv` | Fixed-basket label-shuffle diagnostic for exposure selection; not causal estimates |
| `campaign_daily_comparisons.csv` | Branch/date/weekday adjusted daily results, raw Harbour baseline, trend and pre-period placebo checks |
| `discount_exposure.csv` | Branch/date/category/rate distribution used to identify the 15% windows |
| `discount_accounting.csv` | Recorded list-price concessions by rate, in cents; not savings |
| `assumption_scenarios.csv` | Explicit hypothetical volume lifts, costs, break-even and contribution estimates |
| `quality_and_provenance.json` | Reconciliation, missingness, duplicates, source hash and runtime versions |

Money in basket, comparison and scenario files is USD. Exposure/accounting columns ending `_cents` are integer cents. `coverage` is the fraction of treated records retained; it is not statistical confidence. Blank numeric effects mean no treated/control overlap, never zero effect. Campaign coefficients measure absolute per-day differences relative to changes at controls, assuming parallel absolute trends; they are not randomized treatment effects.

The script validates source arithmetic with a one-cent tolerance, order metadata consistency, expected rates and aggregate reconciliation. The focused unit checks verify aggregation/mixed exposure, a known composition-confounded contrast and explicit no-overlap handling. The full rerun is the integration check; no synthetic fixture is used to support a business claim.
