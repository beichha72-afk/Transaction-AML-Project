"""
data_generator.py

Generates synthetic AML transaction-monitoring data and writes it to CSV
files under ./data/:

    customers.csv     customer_id, full_name, dob, home_jurisdiction, customer_since
    accounts.csv      account_id, customer_id, account_type, open_date
    transactions.csv  transaction_id, account_id, customer_id, timestamp,
                       amount, direction, counterparty, counterparty_jurisdiction,
                       channel
    jurisdictions.csv jurisdiction_code, jurisdiction_name, risk_level

load_db.py (next stage) loads these CSVs into SQLite. The detection logic in
/detections/*.sql queries the loaded tables directly.

PLANTED BAD ACTORS
-------------------
Five customers are deliberately seeded with known-suspicious transaction
patterns, one per typology plus one combo case. Their IDs are fixed
(CUST0001-CUST0005) because they're generated before the random population.
No "is_suspicious" flag is written anywhere in the data itself -- the point
is for the SQL detectors to find them on behavior alone. The answer key is
printed at the end of this script and documented in the README.

Run:
    python data_generator.py
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker


# Config

SEED = 42
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

DATA_DIR = Path(__file__).parent / "data"

N_NORMAL_CUSTOMERS = 150

# Fixed window (not tied to "today") so the dataset is reproducible.
WINDOW_START = datetime(2025, 10, 1)
WINDOW_END = datetime(2025, 12, 31)

# Jurisdiction reference data. HIGH_RISK is an illustrative, FATF-style list
# used only to demonstrate the jurisdiction-exposure typology.
LOW_RISK_JURISDICTIONS = {
    "US": "United States",
    "GB": "United Kingdom",
    "CA": "Canada",
    "DE": "Germany",
    "FR": "France",
    "AU": "Australia",
    "JP": "Japan",
    "SG": "Singapore",
    "NL": "Netherlands",
    "CH": "Switzerland",
    "AE": "United Arab Emirates",
    "HK": "Hong Kong",
}
HIGH_RISK_JURISDICTIONS = {
    "IR": "Iran",
    "KP": "North Korea",
    "MM": "Myanmar",
    "AF": "Afghanistan",
    "SY": "Syria",
}

CHANNELS_NORMAL = ["ACH", "CARD", "WIRE", "CHECK"]
CHANNEL_WEIGHTS_NORMAL = [0.40, 0.35, 0.15, 0.10]

ACCOUNT_TYPES = ["checking", "savings", "business"]


# ID sequences


_customer_seq = 0
_account_seq = 0
_txn_seq = 0


def next_customer_id():
    global _customer_seq
    _customer_seq += 1
    return f"CUST{_customer_seq:04d}"


def next_account_id():
    global _account_seq
    _account_seq += 1
    return f"ACC{_account_seq:05d}"


def next_txn_id():
    global _txn_seq
    _txn_seq += 1
    return f"TXN{_txn_seq:06d}"


# In-memory tables


customers = []
accounts = []
transactions = []

PLANTED_BAD_ACTORS = {}  # customer_id -> description, filled in as we plant them


def create_customer(full_name, home_jurisdiction, customer_since):
    cid = next_customer_id()
    customers.append(
        {
            "customer_id": cid,
            "full_name": full_name,
            "dob": fake.date_of_birth(minimum_age=19, maximum_age=75).isoformat(),
            "home_jurisdiction": home_jurisdiction,
            "customer_since": customer_since.isoformat(),
        }
    )
    return cid


def create_account(customer_id, account_type, open_date):
    aid = next_account_id()
    accounts.append(
        {
            "account_id": aid,
            "customer_id": customer_id,
            "account_type": account_type,
            "open_date": open_date.isoformat(),
        }
    )
    return aid


def make_txn(account_id, customer_id, ts, amount, direction, counterparty, jurisdiction, channel):
    tid = next_txn_id()
    transactions.append(
        {
            "transaction_id": tid,
            "account_id": account_id,
            "customer_id": customer_id,
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "amount": round(amount, 2),
            "direction": direction,
            "counterparty": counterparty,
            "counterparty_jurisdiction": jurisdiction,
            "channel": channel,
        }
    )
    return tid


def add_normal_noise(account_id, customer_id, home_jurisdiction, n):
    """Sprinkle ordinary-looking transactions onto a planted account so it
    isn't made up of 100% suspicious activity -- real bad actors blend in."""
    for _ in range(n):
        ts = random_timestamp(WINDOW_START, WINDOW_END)
        direction = random.choice(["credit", "debit"])
        channel = random.choices(CHANNELS_NORMAL, weights=CHANNEL_WEIGHTS_NORMAL)[0]
        amount = round(random.uniform(20, 3000) + random.random(), 2)
        counterparty = fake.company() if channel in ("ACH", "WIRE") else fake.name()
        make_txn(account_id, customer_id, ts, amount, direction, counterparty, home_jurisdiction, channel)


def random_timestamp(start, end):
    delta_seconds = int((end - start).total_seconds())
    offset = random.randint(0, delta_seconds)
    return start + timedelta(seconds=offset)


# Planted bad actors - one per typology, plus one combo case


def plant_structuring_actor():
    """Typology 1: multiple cash deposits just under the $10,000 CTR
    threshold, clustered within a 48-hour window. Repeated twice to show a
    pattern rather than a one-off."""
    cid = create_customer("Marcus Webb", "US", WINDOW_START - timedelta(days=400))
    aid = create_account(cid, "checking", WINDOW_START - timedelta(days=400))

    burst_1 = WINDOW_START + timedelta(days=20, hours=9)
    for i, amt in enumerate([9200.00, 8700.50, 9450.00, 8990.25]):
        ts = burst_1 + timedelta(hours=i * 9)  # spans ~27 hours, within 48h
        make_txn(aid, cid, ts, amt, "credit", "Cash Deposit - Branch 12", "US", "CASH")

    burst_2 = burst_1 + timedelta(days=25)
    for i, amt in enumerate([9600.00, 8850.75, 9100.00]):
        ts = burst_2 + timedelta(hours=i * 10)
        make_txn(aid, cid, ts, amt, "credit", "Cash Deposit - Branch 12", "US", "CASH")

    add_normal_noise(aid, cid, "US", n=6)
    PLANTED_BAD_ACTORS[cid] = "Structuring: two bursts of sub-$10k cash deposits within 48h windows"
    return cid


def plant_rapid_movement_actor():
    """Typology 2: a large credit followed almost immediately by debits that
    drain most of the balance back out, repeated across two cycles."""
    cid = create_customer("Elena Popov", "GB", WINDOW_START - timedelta(days=200))
    aid = create_account(cid, "checking", WINDOW_START - timedelta(days=200))

    def cycle(start_day, credit_amt, debit_amts, debit_jurisdictions):
        t_in = WINDOW_START + timedelta(days=start_day, hours=10)
        make_txn(aid, cid, t_in, credit_amt, "credit", "Global Trading Partners Ltd", "SG", "WIRE")
        for i, (amt, juris) in enumerate(zip(debit_amts, debit_jurisdictions)):
            ts = t_in + timedelta(hours=20 + i * 6)
            make_txn(aid, cid, ts, amt, "debit", f"Overseas Holdings {i + 1}", juris, "WIRE")

    cycle(15, 42000.00, [14000.00, 13800.00, 13950.00], ["SG", "AE", "HK"])
    cycle(55, 31000.00, [15200.00, 15300.00], ["AE", "HK"])

    add_normal_noise(aid, cid, "GB", n=6)
    PLANTED_BAD_ACTORS[cid] = "Rapid movement: large inbound wires drained back out within ~24-48h, twice"
    return cid


def plant_round_dollar_actor():
    """Typology 3: unusually frequent exactly-round transaction amounts,
    versus normal customers whose amounts carry realistic cents."""
    cid = create_customer("David Okafor", "CA", WINDOW_START - timedelta(days=600))
    aid = create_account(cid, "business", WINDOW_START - timedelta(days=600))

    round_amounts = [1000, 2000, 5000, 10000, 3000, 7000, 1000, 5000, 2000, 4000]
    for i, amt in enumerate(round_amounts):
        ts = WINDOW_START + timedelta(days=5 + i * 7, hours=random.randint(9, 17))
        direction = random.choice(["credit", "debit"])
        make_txn(aid, cid, ts, float(amt), direction, fake.company(), "CA", "WIRE")

    add_normal_noise(aid, cid, "CA", n=6)
    PLANTED_BAD_ACTORS[cid] = "Round-dollar: 10 exactly-round wire amounts over the quarter"
    return cid


def plant_high_risk_jurisdiction_actor():
    """Typology 4: recurring transactions with counterparties in flagged
    high-risk jurisdictions."""
    cid = create_customer("Farid Nazari", "DE", WINDOW_START - timedelta(days=300))
    aid = create_account(cid, "checking", WINDOW_START - timedelta(days=300))

    for i in range(8):
        ts = WINDOW_START + timedelta(days=3 + i * 9, hours=random.randint(9, 17))
        amt = round(random.uniform(3000, 9500) + random.random(), 2)
        direction = random.choice(["credit", "debit"])
        jurisdiction = random.choice(list(HIGH_RISK_JURISDICTIONS))
        make_txn(aid, cid, ts, amt, direction, fake.company(), jurisdiction, "WIRE")

    add_normal_noise(aid, cid, "DE", n=6)
    PLANTED_BAD_ACTORS[cid] = "High-risk jurisdiction: 8 wires to/from FATF-style flagged countries"
    return cid


def plant_combo_actor():
    """Combo case: structuring-style sub-$10k deposits that are ALSO tied to
    high-risk jurisdictions -- a harder validation target where two signals
    should compound."""
    cid = create_customer("Nadia Petrova", "FR", WINDOW_START - timedelta(days=250))
    aid = create_account(cid, "checking", WINDOW_START - timedelta(days=250))

    base = WINDOW_START + timedelta(days=40, hours=9)
    for i, amt in enumerate([9300.00, 8600.00, 9750.00]):
        ts = base + timedelta(hours=i * 8)
        jurisdiction = random.choice(list(HIGH_RISK_JURISDICTIONS))
        make_txn(aid, cid, ts, amt, "credit", "Wire In - Correspondent Bank", jurisdiction, "WIRE")

    add_normal_noise(aid, cid, "FR", n=6)
    PLANTED_BAD_ACTORS[cid] = "Combo: sub-$10k deposits sourced from high-risk jurisdictions"
    return cid


# Normal population



def generate_normal_customer():
    home_jurisdiction = random.choices(
        population=list(LOW_RISK_JURISDICTIONS) + list(HIGH_RISK_JURISDICTIONS),
        weights=[10] * len(LOW_RISK_JURISDICTIONS) + [1] * len(HIGH_RISK_JURISDICTIONS),
    )[0]
    since = WINDOW_START - timedelta(days=random.randint(60, 3000))
    cid = create_customer(fake.name(), home_jurisdiction, since)

    n_accounts = random.choices([1, 2], weights=[0.85, 0.15])[0]
    for _ in range(n_accounts):
        account_type = random.choices(ACCOUNT_TYPES, weights=[0.55, 0.30, 0.15])[0]
        open_date = since + timedelta(days=random.randint(0, 30))
        aid = create_account(cid, account_type, open_date)

        n_txns = random.randint(5, 40)
        for _ in range(n_txns):
            ts = random_timestamp(WINDOW_START, WINDOW_END)
            direction = random.choices(["credit", "debit"], weights=[0.45, 0.55])[0]
            channel = random.choices(CHANNELS_NORMAL, weights=CHANNEL_WEIGHTS_NORMAL)[0]
            amount = round(random.uniform(15, 12000) + random.random(), 2)


            jurisdiction = random.choices(
                population=[home_jurisdiction] + list(LOW_RISK_JURISDICTIONS) + list(HIGH_RISK_JURISDICTIONS),
                weights=[10] + [2] * len(LOW_RISK_JURISDICTIONS) + [0.3] * len(HIGH_RISK_JURISDICTIONS),
            )[0]

            counterparty = fake.company() if channel in ("ACH", "WIRE") else fake.name()
            make_txn(aid, cid, ts, amount, direction, counterparty, jurisdiction, channel)


# CSV output


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    DATA_DIR.mkdir(exist_ok=True)

    # Plant bad actors first so their IDs are fixed at CUST0001-CUST0005.
    plant_structuring_actor()
    plant_rapid_movement_actor()
    plant_round_dollar_actor()
    plant_high_risk_jurisdiction_actor()
    plant_combo_actor()

    for _ in range(N_NORMAL_CUSTOMERS):
        generate_normal_customer()

    write_csv(
        DATA_DIR / "customers.csv",
        customers,
        ["customer_id", "full_name", "dob", "home_jurisdiction", "customer_since"],
    )
    write_csv(
        DATA_DIR / "accounts.csv",
        accounts,
        ["account_id", "customer_id", "account_type", "open_date"],
    )
    write_csv(
        DATA_DIR / "transactions.csv",
        transactions,
        [
            "transaction_id",
            "account_id",
            "customer_id",
            "timestamp",
            "amount",
            "direction",
            "counterparty",
            "counterparty_jurisdiction",
            "channel",
        ],
    )

    jurisdiction_rows = [
        {"jurisdiction_code": code, "jurisdiction_name": name, "risk_level": "LOW"}
        for code, name in LOW_RISK_JURISDICTIONS.items()
    ] + [
        {"jurisdiction_code": code, "jurisdiction_name": name, "risk_level": "HIGH"}
        for code, name in HIGH_RISK_JURISDICTIONS.items()
    ]
    write_csv(
        DATA_DIR / "jurisdictions.csv",
        jurisdiction_rows,
        ["jurisdiction_code", "jurisdiction_name", "risk_level"],
    )

    print(f"Generated {len(customers)} customers, {len(accounts)} accounts, {len(transactions)} transactions.")
    print(f"Written to {DATA_DIR}/\n")
    print("Planted bad actors (ground truth for validating detectors):")
    for cid, description in PLANTED_BAD_ACTORS.items():
        print(f"  {cid}: {description}")


if __name__ == "__main__":
    main()
