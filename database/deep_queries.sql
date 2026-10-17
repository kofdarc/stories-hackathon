-- Deeper business-insight queries for the Stories SQLite database.
-- Run all: sqlite3 -header -column database/stories.sqlite < database/deep_queries.sql
-- Money is stored as integer cents; divide by 100.0 only for display.
-- Gross profit (GP) excludes labor, rent and other operating expenses.

-- 1. Customer concentration: what share of identified GP comes from the top decile?
WITH customer_gp AS (
    SELECT customer_id, SUM(order_gross_profit_cents) AS gp_cents
    FROM orders WHERE customer_id IS NOT NULL GROUP BY customer_id
), ranked AS (
    SELECT gp_cents, NTILE(10) OVER (ORDER BY gp_cents DESC) AS decile FROM customer_gp
)
SELECT decile, COUNT(*) AS customers,
       ROUND(SUM(gp_cents) / 100.0, 2) AS gp_usd,
       ROUND(100.0 * SUM(gp_cents) / (SELECT SUM(gp_cents) FROM customer_gp), 1) AS pct_of_identified_gp
FROM ranked GROUP BY decile ORDER BY decile;

-- 2. Monthly cohort retention: of customers first seen in month M, what % return in M+1, M+2, M+3?
--    NULL means that month is past the end of the data. The Jan cohort includes pre-existing regulars.
WITH last_month AS (SELECT substr(MAX(order_date), 1, 7) AS m FROM orders),
first_seen AS (
    SELECT customer_id, MIN(substr(order_date, 1, 7)) AS cohort
    FROM orders WHERE customer_id IS NOT NULL GROUP BY customer_id
), activity AS (
    SELECT DISTINCT o.customer_id, f.cohort, substr(o.order_date, 1, 7) AS active_month
    FROM orders o JOIN first_seen f USING (customer_id)
), offsets AS (
    SELECT cohort, COUNT(DISTINCT customer_id) AS cohort_size,
           SUM(active_month = substr(date(cohort || '-01', '+1 month'), 1, 7)) AS m1,
           SUM(active_month = substr(date(cohort || '-01', '+2 months'), 1, 7)) AS m2,
           SUM(active_month = substr(date(cohort || '-01', '+3 months'), 1, 7)) AS m3
    FROM activity GROUP BY cohort
)
SELECT cohort, cohort_size,
       CASE WHEN substr(date(cohort || '-01', '+1 month'), 1, 7) <= (SELECT m FROM last_month) THEN ROUND(100.0 * m1 / cohort_size, 1) END AS m1_pct,
       CASE WHEN substr(date(cohort || '-01', '+2 months'), 1, 7) <= (SELECT m FROM last_month) THEN ROUND(100.0 * m2 / cohort_size, 1) END AS m2_pct,
       CASE WHEN substr(date(cohort || '-01', '+3 months'), 1, 7) <= (SELECT m FROM last_month) THEN ROUND(100.0 * m3 / cohort_size, 1) END AS m3_pct
FROM offsets ORDER BY cohort;

-- 3. RFM-style segments as of the last date in the data.
WITH asof AS (SELECT MAX(order_date) AS d FROM orders),
cust AS (
    SELECT customer_id,
           CAST(julianday((SELECT d FROM asof)) - julianday(MAX(order_date)) AS INTEGER) AS days_since_last,
           COUNT(*) AS orders, SUM(order_gross_profit_cents) AS gp_cents
    FROM orders WHERE customer_id IS NOT NULL GROUP BY customer_id
)
SELECT CASE
         WHEN orders >= 10 AND days_since_last <= 30 THEN '1 Loyal & active'
         WHEN orders >= 10                          THEN '2 Loyal, lapsing (>30d)'
         WHEN orders >= 3  AND days_since_last <= 30 THEN '3 Regular & active'
         WHEN orders >= 3                           THEN '4 Regular, lapsing'
         WHEN days_since_last <= 30                 THEN '5 New / occasional'
         ELSE '6 One-off, gone' END AS segment,
       COUNT(*) AS customers,
       ROUND(AVG(orders), 1) AS avg_orders,
       ROUND(SUM(gp_cents) / 100.0, 2) AS gp_usd,
       ROUND(SUM(gp_cents) / 100.0 / COUNT(*), 2) AS gp_per_customer
FROM cust GROUP BY segment ORDER BY segment;

-- 4. Daypart x branch economics: where are the profitable hours?
SELECT branch,
       CASE WHEN CAST(substr(order_time, 1, 2) AS INTEGER) < 11 THEN '1 Morning (<11)'
            WHEN CAST(substr(order_time, 1, 2) AS INTEGER) < 15 THEN '2 Midday (11-15)'
            WHEN CAST(substr(order_time, 1, 2) AS INTEGER) < 19 THEN '3 Afternoon (15-19)'
            ELSE '4 Evening (19+)' END AS daypart,
       COUNT(*) AS orders,
       ROUND(AVG(order_revenue_cents) / 100.0, 2) AS avg_ticket_usd,
       ROUND(AVG(order_gross_profit_cents) / 100.0, 2) AS gp_per_order_usd,
       ROUND(100.0 * SUM(order_gross_profit_cents) / SUM(order_revenue_cents), 1) AS gp_margin_pct
FROM orders GROUP BY branch, daypart ORDER BY branch, daypart;

-- 5. Discount margin erosion: GP given up by product (list-price GP minus actual GP).
SELECT product, category,
       SUM(discount_basis_points > 0) AS discounted_lines,
       ROUND(SUM(CASE WHEN discount_basis_points > 0 THEN quantity * unit_price_cents - line_revenue_cents END) / 100.0, 2) AS discount_cost_usd,
       ROUND(100.0 * SUM(discount_basis_points > 0) / COUNT(*), 1) AS pct_lines_discounted,
       ROUND(100.0 * SUM(line_gross_profit_cents) / SUM(line_revenue_cents), 1) AS gp_margin_pct
FROM transaction_lines
GROUP BY product, category
HAVING discounted_lines > 0
ORDER BY discount_cost_usd DESC LIMIT 15;

-- 6. Market-basket lift: which product pairs co-occur more than chance?
--    lift > 1 means they appear together more often than independent buying predicts.
WITH baskets AS (SELECT DISTINCT transaction_id, product FROM transaction_lines),
n AS (SELECT COUNT(DISTINCT transaction_id) AS total FROM baskets),
item AS (SELECT product, COUNT(*) AS cnt FROM baskets GROUP BY product),
pairs AS (
    SELECT a.product AS a, b.product AS b, COUNT(*) AS together
    FROM baskets a JOIN baskets b ON a.transaction_id = b.transaction_id AND a.product < b.product
    GROUP BY a.product, b.product
)
SELECT p.a, p.b, p.together,
       ROUND(1.0 * p.together / ia.cnt, 3) AS conf_a_to_b,
       ROUND(1.0 * p.together * n.total / (ia.cnt * ib.cnt), 2) AS lift
FROM pairs p JOIN item ia ON ia.product = p.a JOIN item ib ON ib.product = p.b, n
WHERE p.together >= 50
ORDER BY lift DESC LIMIT 15;

-- 7. Upsell headroom: single-item orders by branch and order type, and the GP gap vs multi-item orders.
SELECT branch, order_type,
       COUNT(*) AS orders,
       ROUND(100.0 * SUM(item_lines = 1) / COUNT(*), 1) AS pct_single_item,
       ROUND(AVG(CASE WHEN item_lines = 1 THEN order_gross_profit_cents END) / 100.0, 2) AS gp_single_usd,
       ROUND(AVG(CASE WHEN item_lines > 1 THEN order_gross_profit_cents END) / 100.0, 2) AS gp_multi_usd
FROM orders GROUP BY branch, order_type ORDER BY pct_single_item DESC;

-- 8. Rising and falling products: Jan-Mar vs Apr-Jun units, with GP impact.
WITH q AS (
    SELECT product,
           SUM(CASE WHEN order_date < '2026-04-01' THEN quantity ELSE 0 END) AS units_q1,
           SUM(CASE WHEN order_date >= '2026-04-01' THEN quantity ELSE 0 END) AS units_q2,
           SUM(CASE WHEN order_date >= '2026-04-01' THEN line_gross_profit_cents ELSE -line_gross_profit_cents END) AS gp_delta_cents
    FROM transaction_lines GROUP BY product
)
SELECT product, units_q1, units_q2,
       ROUND(100.0 * (units_q2 - units_q1) / units_q1, 1) AS unit_growth_pct,
       ROUND(gp_delta_cents / 100.0, 2) AS gp_change_usd
FROM q ORDER BY unit_growth_pct DESC;

-- 9. Price consistency: does the same product sell at different list prices across branches?
SELECT product,
       GROUP_CONCAT(branch || ' $' || printf('%.2f', p / 100.0), ', ') AS list_price_by_branch,
       ROUND((MAX(p) - MIN(p)) / 100.0, 2) AS spread_usd
FROM (SELECT product, branch, MAX(unit_price_cents) AS p FROM transaction_lines GROUP BY product, branch)
GROUP BY product HAVING spread_usd > 0 ORDER BY spread_usd DESC LIMIT 15;

-- 10. Visit frequency: average gap since the customer's previous visit, by the branch of the return visit.
WITH visits AS (
    SELECT customer_id, branch, order_date,
           julianday(order_date) - julianday(LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_time)) AS gap_days
    FROM orders WHERE customer_id IS NOT NULL
)
SELECT branch,
       COUNT(gap_days) AS repeat_visits,
       ROUND(AVG(gap_days), 1) AS avg_gap_days,
       ROUND(100.0 * SUM(gap_days <= 7) / COUNT(gap_days), 1) AS pct_within_week
FROM visits GROUP BY branch ORDER BY avg_gap_days;

-- 11. Cross-branch customers: do multi-branch customers spend more?
WITH c AS (
    SELECT customer_id, COUNT(DISTINCT branch) AS branches, COUNT(*) AS orders,
           SUM(order_gross_profit_cents) AS gp_cents
    FROM orders WHERE customer_id IS NOT NULL GROUP BY customer_id
)
SELECT branches, COUNT(*) AS customers, ROUND(AVG(orders), 1) AS avg_orders,
       ROUND(AVG(gp_cents) / 100.0, 2) AS avg_gp_usd
FROM c GROUP BY branches ORDER BY branches;

-- 12. Rolling 7-day GP per branch with week-over-week change (trend + anomaly spotting).
--     Assumes every branch trades every day, so 7 rows back = 7 days back.
WITH daily AS (
    SELECT branch, order_date, SUM(order_gross_profit_cents) AS gp_cents
    FROM orders GROUP BY branch, order_date
), rolled AS (
    SELECT branch, order_date,
           SUM(gp_cents) OVER w7 AS gp7
    FROM daily
    WINDOW w7 AS (PARTITION BY branch ORDER BY order_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
), with_prev AS (
    SELECT branch, order_date, gp7,
           LAG(gp7, 7) OVER (PARTITION BY branch ORDER BY order_date) AS gp7_prev
    FROM rolled
)
SELECT branch, order_date AS week_ending,
       ROUND(gp7 / 100.0, 2) AS gp_7d_usd,
       ROUND(100.0 * (gp7 - gp7_prev) / gp7_prev, 1) AS wow_pct
FROM with_prev
WHERE strftime('%w', order_date) = '0'   -- one row per week (Sundays)
ORDER BY branch, order_date;
