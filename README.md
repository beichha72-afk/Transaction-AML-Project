```
AML Transaction Learning Project
This project was geared towards learning the principles and rules applied in Anti-Money Laundering
systems in financial institutions.

Using Python, SQL, SQLite, I was able to reproduce synthetic transaction data and history in a database
to apply AML rules by using SQL queries.

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
```
