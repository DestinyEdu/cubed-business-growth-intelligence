"""Synthetic accounts and product holdings (part 2). ALL DATA IS FICTIONAL."""
import random
from datetime import date, timedelta

from src.config import RANDOM_SEED
from src.product_catalogue import PRODUCT_NAMES

TODAY = date(2026, 10, 31)
ANOMALY_RATE = 0.015   # accounts deliberately opened before the business was established
ACCOUNT_CODE = {"Business Cheque Account": "BCA",
                "Business Savings Account": "SAV",
                "Notice Deposit Account": "NTD"}
MISSING = {"account_type": 0.02, "open_date": 0.04, "holding_start": 0.05}


def generate_accounts_and_holdings(conn):
    rng = random.Random(RANDOM_SEED + 1)   # separate seed: part 1 data is unaffected

    def rdate(a, b):
        if b <= a:
            return a
        return a + timedelta(days=rng.randint(0, (b - a).days))

    def miss(value, rate):
        return None if rng.random() < rate else value

    businesses = conn.execute(
        "SELECT business_id, industry_sector, employee_count, date_established "
        "FROM businesses ORDER BY business_id").fetchall()

    acc_seq = 0
    for business_id, sector, employees, established in businesses:
        est = date.fromisoformat(established) if established else None
        earliest = max(est, date(2008, 1, 1)) if est else date(2008, 1, 1)
        earliest = min(earliest, date(2026, 6, 30))

        types = ["Business Cheque Account"]
        if rng.random() < 0.35:
            types.append("Business Savings Account")
        if rng.random() < 0.12:
            types.append("Notice Deposit Account")

        cheque_id, cheque_open = None, None
        for t in types:
            acc_seq += 1
            opened = rdate(earliest, TODAY - timedelta(days=30))
            if est and rng.random() < ANOMALY_RATE:
                opened = est - timedelta(days=rng.randint(30, 400))   # deliberate anomaly
            if t == "Business Cheque Account":
                status = rng.choices(["Open", "Dormant"], weights=[96, 4])[0]
            else:
                status = rng.choices(["Open", "Dormant", "Closed"], weights=[94, 4, 2])[0]

            cur = conn.execute(
                "INSERT INTO accounts (business_id, account_ref, account_type, open_date, status) "
                "VALUES (?,?,?,?,?)",
                (business_id, f"SYN-ACC-{acc_seq:08d}",
                 miss(t, MISSING["account_type"]),
                 miss(opened.isoformat(), MISSING["open_date"]), status))
            account_id = cur.lastrowid
            if t == "Business Cheque Account":
                cheque_id, cheque_open = account_id, opened

            code = ACCOUNT_CODE[t]
            conn.execute(
                "INSERT INTO product_holdings (business_id, account_id, product_code, product_name, start_date, status) "
                "VALUES (?,?,?,?,?,?)",
                (business_id, account_id, code, PRODUCT_NAMES[code],
                 miss(opened.isoformat(), MISSING["holding_start"]),
                 "Closed" if status == "Closed" else "Active"))

        # Other products, with realistic tendencies
        retail_like = sector in ("Retail", "Hospitality")
        asset_heavy = sector in ("Transport and Logistics", "Construction", "Agriculture")
        chances = [
            ("CAS", 0.50 if retail_like else 0.20),
            ("PAY", 0.35 if (employees or 0) >= 10 else 0.10),
            ("CCD", 0.18),
            ("OVD", 0.15),
            ("INS", 0.14),
            ("VAF", 0.25 if asset_heavy else 0.06),
        ]
        linked_to_cheque = {"CAS", "PAY", "CCD", "OVD"}
        for code, p in chances:
            if rng.random() < p:
                start = rdate(cheque_open + timedelta(days=30), TODAY)
                conn.execute(
                    "INSERT INTO product_holdings (business_id, account_id, product_code, product_name, start_date, status) "
                    "VALUES (?,?,?,?,?,?)",
                    (business_id, cheque_id if code in linked_to_cheque else None,
                     code, PRODUCT_NAMES[code],
                     miss(start.isoformat(), MISSING["holding_start"]),
                     rng.choices(["Active", "Closed"], weights=[92, 8])[0]))
