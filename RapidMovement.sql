-- Query for rapid movement of funds through an account
-- Where a large inflow is followed by large outflows within a 72h window.

SELECT
    c.account_id,
    c.customer_id,
    c.transaction_id AS inflow_id,
    c.timestamp AS inflow_timestamp,
    c.amount AS inflow_amount,
    SUM(d.amount) AS outflow_amount,
    -- Creates a ratio of outflow to inflow to identify rapid movement based on amounts
    -- Denominator is inflow amount
    SUM(d.amount) / c.amount AS pass_through_ratio
FROM vw_transactions c
    -- Join: c = inflow, d = outflow
LEFT JOIN vw_transactions d ON d.account_id = c.account_id
    AND d.direction = 'debit'
    -- Outflow must occur after inflow and within 3 days (72 hours)
    AND d.timestamp > c.timestamp
    AND julianday(d.timestamp) - julianday(c.timestamp) <= 3
WHERE c.direction = 'credit'
    -- Floor inflow amount to large enough amounts worth laundering
    -- Removing this filter resulted in a lot of false positives
    -- Especially for accounts with many small deposits and withdrawals
    AND c.amount >= 25000
GROUP BY c.transaction_id
    -- Aggregate filter used HAVING instead of WHERE, used SQLite
    -- Stricter SQL engines may require full espression
HAVING pass_through_ratio >= 0.6;

-- Limitations
-- Overlapping, 2 inflows can share the same outflows
-- So a single outflow can be counted multiple times for different inflows
-- And a ratio can exceed 1.0 if the outflow is larger than the inflow

-- False Positives, Payrool processors, merchants, and other businesses
-- That have large inflows and outflows within a 72h window will be flagged

-- Scope, single account, single inflow, and all outflows within 72h of that inflow