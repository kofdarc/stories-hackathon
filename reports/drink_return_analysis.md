# Last drinks and 30-day return behavior

**Decision: no drink should be discontinued from this analysis alone.** 0 drink(s) have a higher adjusted non-return association after a 5% false-discovery correction in the May cohort. Associations are not causes.

The data ends 2026-06-30. Of 3,494 identified customers, 969 had made no purchase in the last 30 days; 944 of these had at least one recorded drink order. Their latest drink-containing basket is counted descriptively. A basket can contain several drinks, so counts overlap. Customers can return after the file ends.

## A fairer comparison than ranking final drinks

Use one first drink-containing order in May per identified customer (1,939 customers). Follow every index purchase for 30 complete calendar days; a return is any identified purchase on a later date within that window, including food-only orders. Overall non-return was 29.4%. June index purchases are excluded because their full follow-up is unavailable.

Each drink is compared with other drink baskets, adjusting for branch, week within May, prior-90-day purchase frequency and average basket spend, time since the preceding purchase, and whether the customer has any earlier observed visit. These histories are only what this file observes. Each model uses one row per customer. Multiple drinks on one order create overlapping exposures. Odds ratios are not relative risks.

Unpenalized logistic models require at least 30 exposed customers and five outcomes of each kind. Wald intervals and tests are exploratory; Benjamini–Hochberg correction covers all successfully fitted May product tests. April uses the same design as a consistency check, not independent replication because customers can overlap.

| Drink | May customers | No return within 30 days | Adjusted odds ratio (95% interval) | Adjusted q | Inactive customers’ last drink |
|---|---:|---:|---:|---:|---:|
| Fresh Orange Juice | 65 | 36.9% | 1.40 (0.84–2.35) | 0.919 | 31 |
| Cold Brew | 109 | 36.7% | 1.39 (0.93–2.09) | 0.919 | 57 |
| English Breakfast Tea | 36 | 36.1% | 1.40 (0.70–2.80) | 0.919 | 18 |
| Classic Matcha | 166 | 34.3% | 1.29 (0.92–1.80) | 0.919 | 80 |
| Spanish Latte | 100 | 34.0% | 1.25 (0.81–1.91) | 0.919 | 50 |
| Sparkling Water | 69 | 31.9% | 1.16 (0.69–1.95) | 0.957 | 39 |
| Iced Matcha | 168 | 30.4% | 1.07 (0.76–1.51) | 0.958 | 80 |
| Chai Latte | 90 | 30.0% | 1.01 (0.63–1.60) | 0.996 | 41 |
| Vanilla Latte | 108 | 29.6% | 1.02 (0.67–1.57) | 0.996 | 53 |
| Mint Tea | 55 | 29.1% | 1.00 (0.55–1.81) | 0.996 | 24 |
| Caramel Latte | 101 | 28.7% | 0.96 (0.61–1.49) | 0.975 | 46 |
| Cappuccino | 133 | 28.6% | 0.96 (0.65–1.42) | 0.975 | 55 |
| Iced Latte | 217 | 28.6% | 0.94 (0.68–1.28) | 0.958 | 104 |
| Coffee Frappe | 64 | 28.1% | 0.95 (0.54–1.65) | 0.975 | 40 |
| Flat White | 119 | 27.7% | 0.92 (0.61–1.40) | 0.958 | 56 |
| Strawberry Matcha | 120 | 26.7% | 0.87 (0.57–1.32) | 0.919 | 63 |
| Still Water | 95 | 26.3% | 0.85 (0.53–1.37) | 0.919 | 57 |
| Lemonade | 84 | 26.2% | 0.83 (0.51–1.37) | 0.919 | 28 |
| Americano | 92 | 26.1% | 0.84 (0.52–1.36) | 0.919 | 45 |
| Peach Iced Tea | 96 | 25.0% | 0.79 (0.49–1.26) | 0.919 | 34 |
| Espresso | 58 | 24.1% | 0.75 (0.41–1.39) | 0.919 | 27 |
| Iced Americano | 130 | 23.8% | 0.75 (0.49–1.13) | 0.919 | 58 |
| Iced Mocha | 76 | 23.7% | 0.74 (0.43–1.28) | 0.919 | 44 |

## What would justify a menu decision?

Use a repeatedly elevated association to prioritize a quality and recipe audit, complaints review, stockout check and comparison of customer mix. Then run a limited controlled recipe or menu-placement test. Track repeat visits, total gross profit, customer satisfaction and substitution into other products. Removing a profitable drink can lose loyal customers; customer preference and visit frequency can explain an observational association.

Customer IDs are missing on 36.5% of orders. Anonymous customers cannot be tracked, and identification may be selective. Non-return within 30 days is not permanent churn. No satisfaction ratings, complaints, stockouts, acquisition channels or reasons for leaving are recorded. All source rows are retained, including possible duplicate item lines; drink exposures use distinct product presence.

Source: `database/stories.sqlite`. Reproduce with `python scripts/drink_return_analysis.py` in an environment with NumPy. Aggregate results: `reports/tables/drink_30day_return.csv`. No customer IDs are exported.
