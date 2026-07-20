SELECT
    t.account_id,
    t.customer_id,
    COUNT(*) AS total_txn_count,
    -- CASE statements to count transactions based on risk levels
    SUM(CASE WHEN j.risk_level = 'HIGH' THEN 1 ELSE 0 END) AS high_risk_txn_count,
    SUM(CASE WHEN j.risk_level = 'MEDIUM' THEN 1 ELSE 0 END) AS medium_risk_txn_count,
    SUM(CASE WHEN j.risk_level = 'LOW' THEN 1 ELSE 0 END) AS low_risk_txn_count
FROM vw_transactions t
    -- JOIN with the jurisdictions table to get the risk level of each transaction's counterparty jurisdiction
JOIN jurisdictions j ON t.counterparty_jurisdiction = j.jurisdiction_code
GROUP BY t.account_id, t.customer_id
    -- Filter to only include accounts with at least 5 high-risk transactions
HAVING SUM(CASE WHEN j.risk_level = 'HIGH' THEN 1 ELSE 0 END) >= 5
ORDER BY high_risk_txn_count DESC;

-- Limitations

-- Inner JOIN drops unmatched transactions
-- Which may lead to underreporting of total transaction counts for accounts 
-- With counterparties in jurisdictions not listed in the jurisdictions table.

-- Static Risk Levels in jurisdictions may not reflect real-time changes from the FATF.

-- Exposure to jurisdictions with high-risk is lawful
-- But may require additional monitoring and reporting based on regulatory requirements.
