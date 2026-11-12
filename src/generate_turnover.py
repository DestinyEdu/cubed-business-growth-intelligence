"""Synthetic six-month turnover and account conduct (part 3). ALL DATA IS FICTIONAL."""
import math
import random

from src.config import RANDOM_SEED

MONTHS = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
PERIOD_END = "2026-10-31"

RETURN_REASONS = ["Insufficient funds", "Debit order disputed by payer", "Mandate cancelled",
                  "Incorrect account details", "Referred to drawer"]
EXPLANATIONS = [
    "Client reports a delayed customer payment; expects normal service next month.",
    "Seasonal cash-flow dip; client has adjusted debit order dates.",
    "Client changed supplier and the old mandate was not cancelled.",
    "Client confirmed the returns were an administrative error and has corrected it.",
    "Large once-off expense in the period; client has rebuilt the account balance.",
]


def generate_turnover_and_conduct(conn):
    rng = random.Random(RANDOM_SEED + 2)   # separate seed: earlier parts are unaffected

    rows = conn.execute("""
        SELECT b.business_id, b.recorded_annual_turnover, m.assigned_bm_id,
               (SELECT h.account_id FROM product_holdings h
                 WHERE h.business_id = b.business_id AND h.product_code = 'BCA'
                   AND h.account_id IS NOT NULL
                 ORDER BY h.holding_id LIMIT 1)
        FROM businesses b JOIN client_master m ON m.client_id = b.client_id
        ORDER BY b.business_id
    """).fetchall()

    for business_id, recorded, bm_id, cheque_id in rows:
        # --- six-month turnover ---------------------------------------------------
        if recorded:
            base = recorded / 12
        else:
            base = rng.lognormvariate(math.log(290_000), 1.0)
        base *= rng.lognormvariate(0, 0.25)      # actual activity differs from recorded figure
        growth = rng.gauss(0.01, 0.03)           # this business's monthly growth direction
        no_system_feed = rng.random() < 0.12     # no system turnover available at all

        for i, month in enumerate(MONTHS):
            value = max(10_000, round(base * (1 + growth) ** i * rng.gauss(1, 0.08), -2))
            system_value = bm_value = captured_by = captured_at = None

            if no_system_feed:
                if rng.random() < 0.30:          # BM captured the month manually
                    source, bm_value = "BM", value
                    captured_by, captured_at = bm_id, f"2026-10-{rng.randint(1, 31):02d}"
                else:
                    source = "MISSING"
            elif rng.random() < 0.05:
                source = "MISSING"               # isolated gap in the system feed
            else:
                system_value, source = value, "SYSTEM"
                if rng.random() < 0.06:          # BM corrects the system value
                    bm_value = round(value * rng.uniform(0.90, 1.15), -2)
                    source = "BM"
                    captured_by, captured_at = bm_id, f"2026-10-{rng.randint(1, 31):02d}"

            conn.execute(
                "INSERT INTO monthly_turnover (business_id, account_id, month, system_value, bm_value, "
                "value_source, captured_by, captured_at) VALUES (?,?,?,?,?,?,?,?)",
                (business_id, cheque_id, month, system_value, bm_value, source, captured_by, captured_at))

        # --- returned debit orders (last six months, cheque account) ---------------
        if cheque_id is None:
            continue
        r = rng.random()
        if r < 0.62:
            returned = 0
        elif r < 0.87:
            returned = rng.randint(1, 2)
        else:
            returned = rng.randint(3, 6)

        reasons = "; ".join(rng.sample(RETURN_REASONS, k=min(returned, 3))) if returned else None
        explain_chance = 0.55 if returned >= 3 else (0.20 if returned >= 1 else 0)
        explained = rng.random() < explain_chance
        conn.execute(
            "INSERT INTO account_conduct (account_id, period_end, returned_debit_orders, return_reasons, "
            "bm_explanation, recorded_by, recorded_at) VALUES (?,?,?,?,?,?,?)",
            (cheque_id, PERIOD_END, returned, reasons,
             rng.choice(EXPLANATIONS) if explained else None,
             bm_id if explained else None,
             f"2026-10-{rng.randint(1, 31):02d}" if explained else None))
