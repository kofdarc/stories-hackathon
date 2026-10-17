-- Run all examples: sqlite3 -header -column database/stories.sqlite < database/queries.sql

-- 1. Business totals (one row per order, so baskets are not double-counted).
SELECT COUNT(*) AS orders,
       ROUND(SUM(order_revenue_cents) / 100.0, 2) AS revenue_usd,
       ROUND(SUM(order_gross_profit_cents) / 100.0, 2) AS gross_profit_usd,
       ROUND(SUM(order_revenue_cents) / 100.0 / COUNT(*), 2) AS average_order_usd
FROM orders;

-- 2. Monthly growth.
SELECT substr(order_date, 1, 7) AS month, COUNT(*) AS orders,
       ROUND(SUM(order_revenue_cents) / 100.0, 2) AS revenue_usd,
       ROUND(SUM(order_revenue_cents) / 100.0 / COUNT(*), 2) AS average_order_usd
FROM orders GROUP BY month ORDER BY month;

-- 3. Branch performance; gross profit excludes operating expenses.
SELECT branch, COUNT(*) AS orders,
       ROUND(SUM(order_revenue_cents) / 100.0, 2) AS revenue_usd,
       ROUND(SUM(order_gross_profit_cents) / 100.0, 2) AS gross_profit_usd,
       ROUND(100.0 * SUM(order_gross_profit_cents) / NULLIF(SUM(order_revenue_cents), 0), 1) AS margin_percent
FROM orders GROUP BY branch ORDER BY gross_profit_usd DESC;

-- 4. Products ranked by gross profit.
SELECT product, category, SUM(quantity) AS units,
       ROUND(SUM(line_revenue_cents) / 100.0, 2) AS revenue_usd,
       ROUND(SUM(line_gross_profit_cents) / 100.0, 2) AS gross_profit_usd,
       ROUND(100.0 * SUM(line_gross_profit_cents) / NULLIF(SUM(line_revenue_cents), 0), 1) AS margin_percent
FROM transaction_lines GROUP BY product, category ORDER BY gross_profit_usd DESC;

-- 5. Hourly demand by branch (order counts, not item-line counts).
SELECT branch, substr(order_time, 1, 2) AS hour_24, COUNT(*) AS orders
FROM orders GROUP BY branch, hour_24 ORDER BY branch, hour_24;

-- 6. Exact-product unit cost benchmark. A gap is not confirmed achievable savings.
WITH peers AS (
    SELECT product, 1.0 * SUM(quantity * unit_cost_cents) / SUM(quantity) AS cost_cents
    FROM transaction_lines WHERE branch <> 'Garden' GROUP BY product
), garden AS (
    SELECT product, SUM(quantity) AS units, SUM(quantity * unit_cost_cents) AS cost_cents
    FROM transaction_lines WHERE branch = 'Garden' GROUP BY product
)
SELECT g.product, g.units,
       ROUND(g.cost_cents / (100.0 * g.units), 2) AS garden_unit_cost_usd,
       ROUND(p.cost_cents / 100.0, 2) AS peer_unit_cost_usd,
       ROUND((g.cost_cents - g.units * p.cost_cents) / 100.0, 2) AS recorded_cost_gap_usd
FROM garden g JOIN peers p USING (product) ORDER BY recorded_cost_gap_usd DESC;

-- 7. Food attachment among drink-containing orders.
WITH baskets AS (
    SELECT transaction_id,
           MAX(category IN ('Hot Coffee', 'Cold Coffee', 'Cold Drinks', 'Matcha & Tea')) AS has_drink,
           MAX(category IN ('Bakery', 'Desserts', 'Breakfast', 'Meals', 'Sandwiches')) AS has_food
    FROM transaction_lines GROUP BY transaction_id
)
SELECT SUM(has_drink) AS drink_orders,
       SUM(has_drink * has_food) AS drink_orders_with_food,
       ROUND(100.0 * SUM(has_drink * has_food) / NULLIF(SUM(has_drink), 0), 1) AS attachment_percent
FROM baskets;

-- 8. Customer ID coverage. Anonymous customers cannot be tracked for retention.
SELECT COUNT(*) AS orders, COUNT(customer_id) AS identified_orders,
       COUNT(DISTINCT customer_id) AS identified_customers,
       ROUND(100.0 * COUNT(customer_id) / COUNT(*), 1) AS identified_order_percent
FROM orders;
