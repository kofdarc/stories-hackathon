PRAGMA foreign_keys = ON;

-- One row per source CSV item line. Transaction IDs repeat for multi-item orders.
-- Store money as integer cents so totals remain exact.
CREATE TABLE transaction_lines (
    line_id INTEGER PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    order_time TEXT NOT NULL,
    branch TEXT NOT NULL,
    customer_id TEXT,
    order_type TEXT NOT NULL,
    product TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
    discount_basis_points INTEGER NOT NULL CHECK (discount_basis_points BETWEEN 0 AND 10000),
    unit_cost_cents INTEGER NOT NULL CHECK (unit_cost_cents >= 0),
    line_revenue_cents INTEGER NOT NULL,
    line_gross_profit_cents INTEGER NOT NULL
);

CREATE INDEX idx_lines_transaction ON transaction_lines(transaction_id);
CREATE INDEX idx_lines_date_branch ON transaction_lines(order_date, branch);
CREATE INDEX idx_lines_branch_product ON transaction_lines(branch, product);
CREATE INDEX idx_lines_customer_date ON transaction_lines(customer_id, order_date);
CREATE INDEX idx_lines_category ON transaction_lines(category);

-- Convenient dollar-denominated columns; raw cents remain available in the table.
CREATE VIEW transactions AS
SELECT line_id, transaction_id, order_date, order_time, branch, customer_id,
       order_type, product, category, quantity,
       unit_price_cents / 100.0 AS unit_price_usd,
       discount_basis_points / 10000.0 AS discount_rate,
       unit_cost_cents / 100.0 AS unit_cost_usd,
       line_revenue_cents / 100.0 AS line_revenue_usd,
       line_gross_profit_cents / 100.0 AS line_gross_profit_usd
FROM transaction_lines;

-- Import validates that all metadata within each transaction agrees.
CREATE VIEW orders AS
SELECT transaction_id, MIN(order_date) AS order_date,
       MIN(order_time) AS order_time, MIN(branch) AS branch,
       MIN(customer_id) AS customer_id, MIN(order_type) AS order_type,
       COUNT(*) AS item_lines, SUM(quantity) AS units,
       SUM(line_revenue_cents) AS order_revenue_cents,
       SUM(line_gross_profit_cents) AS order_gross_profit_cents,
       SUM(line_revenue_cents) / 100.0 AS order_revenue_usd,
       SUM(line_gross_profit_cents) / 100.0 AS order_gross_profit_usd
FROM transaction_lines
GROUP BY transaction_id;

CREATE TABLE source_metadata (
    source_filename TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    line_count INTEGER NOT NULL,
    order_count INTEGER NOT NULL,
    first_date TEXT NOT NULL,
    last_date TEXT NOT NULL
);
