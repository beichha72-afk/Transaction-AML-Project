
-- Query 1: Baseline Calendar Day Structure for Deposits
-- Simple to write but multiple blind spots
-- Deposits at 11pm and 1am are counted as separate days, but they are within 2 hours of each other
-- Day bucketing splits them so they are not counted as a single deposit event, which is a blind spot for fraud detection
SELECT customer_id, 
    DATE(timestamp) AS deposit_day,
    COUNT(*) AS deposit_count,
    SUM(amount) AS total_deposit_amount
FROM vw_transactions
WHERE direction = 'credit'
    AND amount < 10000 -- Threshold for deposits
GROUP BY customer_id, DATE(timestamp)
HAVING COUNT(*) >= 3 -- 3 or more deposits in a single day alerts
ORDER BY deposit_count DESC;


-- Query 2: Rolling 48h Window Structure for Deposits
-- Replaces the fixed calendar day with a window relative to the current deposit timestamp
WITH deposits AS (
    SELECT transaction_id, 
    customer_id, 
    timestamp,
    amount,
    -- Counts customer deposits in a rolling 48h window, including the current deposit
    -- julianday() function converts timestamp to Julian day number, which allows for date arithmetic
    COUNT(*) OVER (PARTITION BY customer_id ORDER BY julianday(timestamp) RANGE BETWEEN 2 PRECEDING AND CURRENT ROW) AS deposits_in_window
    FROM vw_transactions
    WHERE direction = 'credit'
    -- Change amount band to reduce false-postives, improves precision and still catches bad actors (CUST0001) and (CUST0005)
        AND amount BETWEEN 8000 AND 9999
)

SELECT *
FROM deposits
WHERE deposits_in_window >= 3 -- 3 or more deposits in a rolling 48h window alerts
ORDER BY customer_id, timestamp;

-- Limitations

-- False-Positives, cash intensive businesses, payroll processors, and other businesses 
-- That have multiple deposits within a 48h window will be flagged
-- Baselining against customer type or group thresholds would reduce false positives, but that is out of scope for this exercise

-- Patient Structuring, a customer spreading deposits over a 48h window to avoid detection, 
-- But still within a short enough time frame to be considered suspicious

-- Amount bands, assumes structuring clusters between 8k and 10k
-- Amounts lower will not be flagged

-- Cross Institutional Structuring, Deposits across multiple institutions will not be detected, 
-- As the data is limited to a single institution's transactions