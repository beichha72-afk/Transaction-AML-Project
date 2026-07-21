```
AML Transaction Learning Project
This project was geared towards learning the principles and rules applied in Anti-Money Laundering
systems in financial institutions.

Using Python, SQL, SQLite, I was able to reproduce synthetic transaction data and history in a database
to apply AML rules by using SQL queries.

Why this project

Transaction monitoring is the core of any financial institution's AML program.
Rather than a single black-box model, this prototype demonstrates the discipline behind real monitoring: defining a typology as a data pattern, translating it into SQL, tuning thresholds against the precision/recall tradeoff, and documenting where each rule breaks.
Every threshold in the codebase is a defensible judgment call, and every detector carries an explicit limitations section.

The Architecture:
data_generator.py   ->  Generates synthetic customers, accounts, transactions,
                        and a jurisdictions reference table. Seeds five known
                        bad actors (one per typology + one combo case).
load_db.py          ->  Loads the CSVs into a SQLite database (aml.db).
detections          ->  One SQL file per typology, each querying the loaded data.
CorrelationSummary  ->  Aggregates all four detectors to rank customers by how
                        many independent typologies they trigger

The Detectors
Structuring         -> Multiple sub-threshold deposits clustered in a rolling 2-day (48h) window.
Rapid Movement      -> Inflow drained back out of the same account in a 3-day (72h) window.
Round Dollar        -> Disproportionate share of exact round dollar transactions.
Jurisdiction Risk   -> Concentration of activities based on jurisdiction and their risk_level.

There were no direct flags used to seed the bad actors, each were mixed in the ordinary noise of transaction history.
CUST0001 | Structuring
CUST0002 | Rapid Movement
CUST0003 | Round Dollar
CUST0004 | High Risk Jurisdiction
CUST0005 | Combo, sub-threshold deposits from a high risk Jurisdiction

The Correlation Layer: The Most Important

- The most important result of this project was not building each single detector but to build a comprehensive
  correlation summary using all four. This convergence allowed results to show which bad actors and what detectors they triggered,
  which in a real-life instance would allow an analyst to alert or escalate behavior.
- The design of detectors relied on narrow rules over broad rules to apply tuning and adjustable principles that are auditable.

Tech:
Python (Faker for synthetic data), SQLite (database creation), SQL (window functions, self-joins, conditional aggregation, reference-table joins), VS Code 2

Limitations and next steps

This is a prototype on synthetic data. Real deployment would add: baselining against customer type to reduce false positives from cash-intensive and settlement businesses; a customer-level rollup to consolidate exposure fragmented across accounts; versioned jurisdiction risk ratings scored at transaction time; and a feedback loop where analyst dispositions tune thresholds over time.

```
