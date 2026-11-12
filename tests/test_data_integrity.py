import re
import sqlite3

import pytest

from src.config import NUM_CLIENTS
from src.generate_turnover import MONTHS

EXPECTED_TABLES = {
    "client_master", "businesses", "directors", "accounts", "product_holdings",
    "monthly_turnover", "account_conduct", "product_recommendations", "product_rules",
    "discussion_assists", "client_engagements", "crm_pipeline", "users", "audit_logs",
}


def one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


# ---------- structure ----------
def test_all_14_tables_exist(db):
    names = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    assert names == EXPECTED_TABLES


def test_no_foreign_key_violations(db):
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []


# ---------- volumes ----------
def test_volumes(db):
    assert one(db, "SELECT COUNT(*) FROM client_master") == NUM_CLIENTS
    assert one(db, "SELECT COUNT(*) FROM users") == 19
    assert one(db, "SELECT COUNT(*) FROM businesses") >= NUM_CLIENTS


def test_one_cun_can_link_to_several_businesses(db):
    assert one(db, "SELECT COUNT(*) FROM (SELECT client_id FROM businesses GROUP BY 1 HAVING COUNT(*) > 1)") > 0


# ---------- relationships ----------
def test_every_client_has_a_business(db):
    assert one(db, "SELECT COUNT(*) FROM client_master m WHERE NOT EXISTS "
                   "(SELECT 1 FROM businesses b WHERE b.client_id = m.client_id)") == 0


@pytest.mark.parametrize("child", ["directors", "accounts"])
def test_every_business_has_directors_and_accounts(db, child):
    assert one(db, f"SELECT COUNT(*) FROM businesses b WHERE NOT EXISTS "
                   f"(SELECT 1 FROM {child} c WHERE c.business_id = b.business_id)") == 0


def test_every_business_has_exactly_the_six_expected_months(db):
    assert one(db, "SELECT COUNT(*) FROM (SELECT business_id FROM monthly_turnover "
                   "GROUP BY 1 HAVING COUNT(*) <> 6)") == 0
    months = [r[0] for r in db.execute("SELECT DISTINCT month FROM monthly_turnover ORDER BY 1")]
    assert months == MONTHS
    assert one(db, "SELECT COUNT(DISTINCT business_id) FROM monthly_turnover") == \
        one(db, "SELECT COUNT(*) FROM businesses")


def test_holdings_account_belongs_to_the_same_business(db):
    assert one(db, "SELECT COUNT(*) FROM product_holdings h JOIN accounts a USING(account_id) "
                   "WHERE h.business_id <> a.business_id") == 0


def test_turnover_account_belongs_to_the_same_business(db):
    assert one(db, "SELECT COUNT(*) FROM monthly_turnover t JOIN accounts a USING(account_id) "
                   "WHERE t.business_id <> a.business_id") == 0


def test_conduct_is_recorded_only_on_cheque_accounts(db):
    assert one(db, "SELECT COUNT(*) FROM account_conduct k WHERE NOT EXISTS "
                   "(SELECT 1 FROM product_holdings h WHERE h.account_id = k.account_id "
                   "AND h.product_code = 'BCA')") == 0


# ---------- identifiers and synthetic safeguards ----------
def test_cun_and_account_reference_formats(db):
    assert one(db, "SELECT COUNT(*) FROM client_master WHERE cun NOT GLOB 'SYN-' || '[0-9]' || '[0-9]' || "
                   "'[0-9]' || '[0-9]' || '[0-9]' || '[0-9]'") == 0
    assert one(db, "SELECT COUNT(*) FROM accounts WHERE account_ref NOT GLOB 'SYN-ACC-' || "
                   "'[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]'") == 0


def test_every_client_is_flagged_synthetic(db):
    assert one(db, "SELECT COUNT(*) FROM client_master WHERE is_synthetic <> 1") == 0


def test_no_sensitive_number_columns_exist(db):
    banned = re.compile(r"(id_number|identity_number|passport_number|account_number|card_number|national_id)", re.I)
    for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        for col in db.execute(f"PRAGMA table_info({table})"):
            assert not banned.search(col[1]), f"Sensitive-looking column {table}.{col[1]}"


def test_directors_hold_id_category_only(db):
    values = {r[0] for r in db.execute("SELECT DISTINCT id_category FROM directors")}
    assert values <= {"South African ID", "Passport", "Other", None}


# ---------- turnover rules ----------
def test_turnover_source_rules(db):
    assert one(db, "SELECT COUNT(*) FROM monthly_turnover WHERE value_source='SYSTEM' "
                   "AND (system_value IS NULL OR bm_value IS NOT NULL)") == 0
    assert one(db, "SELECT COUNT(*) FROM monthly_turnover WHERE value_source='BM' AND (bm_value IS NULL "
                   "OR captured_by IS NULL OR captured_at IS NULL)") == 0
    assert one(db, "SELECT COUNT(*) FROM monthly_turnover WHERE value_source='MISSING' "
                   "AND (system_value IS NOT NULL OR bm_value IS NOT NULL)") == 0


def test_both_capture_methods_are_represented(db):
    assert one(db, "SELECT COUNT(*) FROM monthly_turnover WHERE value_source='SYSTEM'") > 0
    assert one(db, "SELECT COUNT(*) FROM monthly_turnover WHERE value_source='BM'") > 0
    assert one(db, "SELECT COUNT(*) FROM monthly_turnover WHERE value_source='MISSING'") > 0


def test_bm_corrections_retain_the_original_system_value(db):
    assert one(db, "SELECT COUNT(*) FROM monthly_turnover WHERE value_source='BM' "
                   "AND system_value IS NOT NULL AND bm_value IS NOT NULL") > 0


# ---------- conduct rules ----------
def test_conduct_reason_and_explanation_rules(db):
    assert one(db, "SELECT COUNT(*) FROM account_conduct WHERE returned_debit_orders = 0 "
                   "AND return_reasons IS NOT NULL") == 0
    assert one(db, "SELECT COUNT(*) FROM account_conduct WHERE returned_debit_orders > 0 "
                   "AND return_reasons IS NULL") == 0
    assert one(db, "SELECT COUNT(*) FROM account_conduct WHERE bm_explanation IS NOT NULL "
                   "AND (recorded_by IS NULL OR recorded_at IS NULL)") == 0


def test_all_three_conduct_bands_are_present(db):
    assert one(db, "SELECT COUNT(*) FROM account_conduct WHERE returned_debit_orders = 0") > 0
    assert one(db, "SELECT COUNT(*) FROM account_conduct WHERE returned_debit_orders BETWEEN 1 AND 2") > 0
    assert one(db, "SELECT COUNT(*) FROM account_conduct WHERE returned_debit_orders >= 3") > 0


def test_some_three_plus_cases_still_need_an_explanation(db):
    assert one(db, "SELECT COUNT(*) FROM account_conduct WHERE returned_debit_orders >= 3 "
                   "AND bm_explanation IS NULL") > 0


# ---------- deliberate data-quality gaps ----------
@pytest.mark.parametrize("table,column", [
    ("businesses", "industry_sector"), ("businesses", "province"), ("businesses", "employee_count"),
    ("businesses", "recorded_annual_turnover"), ("businesses", "date_established"),
    ("directors", "id_category"), ("accounts", "open_date"),
])
def test_deliberate_missing_values_are_present_but_limited(db, table, column):
    total = one(db, f"SELECT COUNT(*) FROM {table}")
    missing = one(db, f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")
    assert 0.01 <= missing / total <= 0.15, f"{table}.{column} missing rate {missing / total:.1%}"


def test_some_accounts_predate_their_business(db):
    anomalies = one(db, "SELECT COUNT(*) FROM accounts a JOIN businesses b USING(business_id) "
                        "WHERE a.open_date < b.date_established")
    assert 0 < anomalies < 0.05 * one(db, "SELECT COUNT(*) FROM accounts")


# ---------- the database refuses rule-breaking data ----------
BAD_INSERTS = {
    "disqualified product with score above 0":
        "INSERT INTO product_recommendations (business_id, product_code, take_up_score, eligibility_status) "
        "VALUES (1, 'CAS', 5, 'DISQUALIFIED')",
    "take-up score of 6":
        "INSERT INTO product_recommendations (business_id, product_code, take_up_score, eligibility_status) "
        "VALUES (1, 'CAS', 6, 'ELIGIBLE')",
    "business linked to a client that does not exist":
        "INSERT INTO businesses (client_id, business_name) VALUES (999999, 'Orphan')",
    "rule approved by its own drafter":
        "INSERT INTO product_rules (product_code, rule_name, rule_type, drafted_by, approved_by) "
        "VALUES ('CAS', 'R', 'SCORING', 1, 1)",
    "client not flagged as synthetic":
        "INSERT INTO client_master (cun, client_name, is_synthetic) VALUES ('REAL-1', 'X', 0)",
    "duplicate CUN":
        "INSERT INTO client_master (cun, client_name) VALUES ('SYN-000001', 'Duplicate')",
    "unknown user role":
        "INSERT INTO users (username, full_name, role) VALUES ('x', 'X', 'Superuser')",
    "second turnover row for the same business and month":
        "INSERT INTO monthly_turnover (business_id, month, value_source) VALUES (1, '2026-05', 'MISSING')",
    "negative returned debit orders":
        "INSERT INTO account_conduct (account_id, period_end, returned_debit_orders) VALUES (1, '2026-10-31', -1)",
}


@pytest.mark.parametrize("label", list(BAD_INSERTS))
def test_database_rejects_rule_breaking_data(scratch, label):
    with pytest.raises(sqlite3.IntegrityError):
        scratch.execute(BAD_INSERTS[label])


# ---------- data dictionary stays in sync with the schema ----------
def test_data_dictionary_covers_every_table_and_column(db):
    from src.build_data_dictionary import DESCRIPTIONS, PURPOSE
    for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        assert table in PURPOSE, f"{table} has no purpose statement"
        cols = {c[1] for c in db.execute(f"PRAGMA table_info({table})")}
        documented = set(DESCRIPTIONS.get(table, {}))
        assert cols == documented, f"{table}: undocumented {cols - documented}, stale {documented - cols}"
