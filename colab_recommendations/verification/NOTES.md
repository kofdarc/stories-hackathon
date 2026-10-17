# Verification notes

- **26 tests passed.** Synthetic fixtures verify financial identities, full-basket exposure, discount leakage, closure capacity/exit costs, expiry sunk costs, loyalty reward leakage, delivery channel switching, forecast time isolation, zero-filled calendars, invalid inputs and identifier-free reporting.
- The actual notebook passed `nbformat` validation and executed locally with real ipywidgets and the repository transaction CSV. Authorization, all three branch selectors, recalculation, combo discovery, nine sensitivity curves, chart generation, report ZIP and the local download callback were exercised.
- Every source customer and transaction ID was checked against every text file in the report ZIP; none appeared. The distributed notebook retains no outputs or transaction data. Its embedded engine is checked against `engine.py`.
- The input audited at verification has 51,177 lines / 33,887 baskets and 132 exact repeated rows; no half-cent financial reconciliation failures occurred. See `verification.json` for fingerprints, aggregate checks and forecast scores.
- For the default Garden / Iced Latte calibration, validation selected the trailing-28-day mean. Its final-test MAE was 3.04 units/day and WAPE 54.5%; the weekday baseline scored 2.96 units/day and 53.1%. This weak result does **not** justify claiming a strong forecast advantage. The notebook exposes both models and the final test.
- The ranking chart was visually checked for readable category labels, numeric values, units and horizon. Closure dominates default downside because no avoidable fixed costs or customer migration are credited without assumptions. Small scenario values are labeled explicitly.
- The hosted Colab browser upload/download dialogs were not automated. Runtime setup installation is skipped in local notebook verification because test dependencies are installed separately; the Colab setup cell itself uses standard `%pip` and `google.colab` APIs.

Reproduce from the repository root with the commands in the adjacent README. The notebook generator writes an output-free artifact; verification never copies the input CSV or publishes it.
