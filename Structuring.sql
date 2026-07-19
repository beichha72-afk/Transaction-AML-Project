
 -- Normal approach to find customers with at least 3 deposits of less than $10,000 within a 3-day window using grouping and filtering per customer.

SELECT customer_id, 
    DATE(timestamp) AS deposit_day,
    COUNT(*) AS deposit_count,
    SUM(amount) AS total_deposit_amount
FROM vw_transactions
WHERE direction = 'credit'
    AND amount < 10000
GROUP BY customer_id, DATE(timestamp)
HAVING COUNT(*) >= 3
ORDER BY deposit_count DESC;


-- Window function approach to find customers with at least 3 deposits of less than $10,000 within a 3-day window using more filtering per transaction.

WITH deposits AS (
    SELECT transaction_id, 
    customer_id, 
    timestamp,
    amount,
    COUNT(*) OVER (PARTITION BY customer_id ORDER BY julianday(timestamp) RANGE BETWEEN 2 PRECEDING AND CURRENT ROW) AS deposits_in_window
    FROM vw_transactions
    WHERE direction = 'credit'
    -- Change amount type to reduce false-postives, improves precision and still catches bad actors (CUST0001) and (CUST0005)
        AND amount BETWEEN 8000 AND 9999
)

SELECT *
FROM deposits
WHERE deposits_in_window >= 3
ORDER BY customer_id, timestamp;
