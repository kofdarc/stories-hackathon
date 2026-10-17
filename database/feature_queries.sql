-- Example questions over the enriched view. add_features.py runs these to keep them valid.

-- 1. Baskets and revenue on rainy vs dry days, per branch (daily averages).
-- Raw averages: rainy days cluster in winter, when volume is lower. Seasonally controlled
-- estimates are in reports/external_factors.md.
SELECT branch, rainy, COUNT(DISTINCT order_date) AS days,
       ROUND(COUNT(DISTINCT transaction_id) * 1.0 / COUNT(DISTINCT order_date), 1) AS baskets_per_day,
       ROUND(SUM(line_revenue_usd) / COUNT(DISTINCT order_date), 2) AS revenue_per_day
FROM transactions_enriched GROUP BY branch, rainy ORDER BY branch, rainy;

-- 2. Cold vs hot drink units by temperature band.
SELECT temp_band,
       SUM(CASE WHEN product_type = 'Cold drink' THEN quantity END) AS cold_units,
       SUM(CASE WHEN product_type = 'Hot drink' THEN quantity END) AS hot_units,
       ROUND(SUM(CASE WHEN product_type = 'Cold drink' THEN quantity END) * 1.0 /
             SUM(CASE WHEN product_type IN ('Cold drink', 'Hot drink') THEN quantity END), 3) AS cold_share
FROM transactions_enriched GROUP BY temp_band ORDER BY MIN(temp_mean);

-- 3. Dine-in share when it is raining or dusty at the transaction hour.
SELECT raining_now, dusty_now, COUNT(DISTINCT transaction_id) AS baskets,
       ROUND(AVG(order_type = 'Dine-in'), 3) AS dine_in_line_share
FROM transactions_enriched GROUP BY raining_now, dusty_now;

-- 4. Average basket by daypart and Ramadan.
SELECT daypart, ramadan, COUNT(DISTINCT transaction_id) AS baskets,
       ROUND(SUM(line_revenue_usd) / COUNT(DISTINCT transaction_id), 2) AS revenue_per_basket
FROM transactions_enriched GROUP BY daypart, ramadan ORDER BY daypart, ramadan;

-- 5. Holiday, bridge-day and school-break days vs ordinary days.
SELECT CASE WHEN holiday THEN 'Holiday' WHEN bridge_day THEN 'Bridge day'
            WHEN school_break THEN 'School break' ELSE 'Ordinary' END AS day_type,
       COUNT(DISTINCT order_date) AS days,
       ROUND(COUNT(DISTINCT transaction_id) * 1.0 / COUNT(DISTINCT order_date), 1) AS baskets_per_day
FROM transactions_enriched GROUP BY day_type;

-- 6. Return gap for identified repeat customers, by branch.
SELECT branch, COUNT(*) AS repeat_visits, ROUND(AVG(days_since_prev_visit), 1) AS mean_days_between
FROM (SELECT DISTINCT transaction_id, branch, days_since_prev_visit FROM transactions_enriched
      WHERE customer_repeat = 1) GROUP BY branch;

-- 7. Busiest planning cells: expected June baskets and the Poisson P90 to staff for.
SELECT branch, weekday, hour, ROUND(expected, 1) AS expected_baskets, p90_baskets
FROM staffing_template ORDER BY expected DESC LIMIT 10;
