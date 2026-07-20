-- Query 1: Round Dollar Amounts Detection
-- Detects customers with multiple deposits that are round dollar amounts by multiples of 1000
-- Used as a baseline to compare against Query 2

SELECT 
    customer_id,
    COUNT(*) AS round_txn_amount,
    SUM(amount) AS total_round_amount
FROM vw_transactions
WHERE direction = 'credit'
    -- Roundness check: ROUND(amount) = amount ensures the amount is a whole number
    AND ROUND(amount) = amount 
    AND CAST(amount AS INTEGER) % 1000 = 0
GROUP BY customer_id
HAVING COUNT(*) >= 5 -- 5 or more round dollar deposits alerts, higher threshold to reduce false positives
ORDER BY round_txn_amount DESC;

-- Query 2: Conditional Round Dollar Amounts Detection
SELECT
    customer_id,
    COUNT(*) AS total_txn_count,
    -- CASE statement counts the number of round dollar transactions for each customer = 1
    -- Everything else is marked as 0, which is then summed to get the total count of round dollar transactions
    SUM(CASE WHEN ROUND(amount) = amount
              AND CAST(amount AS INTEGER) % 1000 = 0
             THEN 1 ELSE 0 END) AS round_txn_count,
    -- 1.0 is multiplied to ensure the division results in a float, which allows for decimal precision in the ratio calculation
    SUM(CASE WHEN ROUND(amount) = amount
              AND CAST(amount AS INTEGER) % 1000 = 0
             THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS round_ratio
FROM vw_transactions
WHERE direction = 'credit'
GROUP BY customer_id
HAVING COUNT(*) >= 5 
   AND round_ratio >= 0.5 -- 50% or more of the deposits are round dollar amounts alerts, higher threshold to reduce false positives
ORDER BY round_ratio DESC;

-- Limitations

-- Roundness is a weak signal for fraud detection, as it can be easily manipulated by customers
-- Many legitmate transactions can also be round dollar amounts, which could lead to false positives
-- So this metric should be used in conjunction with other fraud detection methods

-- Multiple amount is abritrary and can be adjusted based on the business context and risk appetite
-- A launderer may choose to deposit amounts that are not round dollar amounts to avoid detection

-- Ratio is unstable at low transaction counts
-- So a minimum transaction count threshold is applied to reduce false positives

-- The time frame of the transactions should also be considered
-- As a customer may have multiple deposits over a long period of time, which may not be suspicious