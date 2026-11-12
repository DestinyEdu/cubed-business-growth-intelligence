import pandas as pd
import pytest

from src.analytics import (
    ALIGNMENT_THRESHOLD, bm_activity, business_turnover_summary, data_quality_report,
    portfolio_overview, product_penetration, turnover_by_dimension, turnover_by_month,
)
from src.generate_turnover import MONTHS

DIRECT_TOTAL_SQL = "SELECT SUM(COALESCE(bm_value, system_value)) FROM monthly_turnover"


def one(conn, sql):
    return conn.execute(sql).fetchone()[0]


# ---------- overview ----------
def test_overview_counts_match_the_database(db):
    o = portfolio_overview(db)
    assert o["clients"] == one(db, "SELECT COUNT(*) FROM client_master")
    assert o["businesses"] == one(db, "SELECT COUNT(*) FROM businesses")
    assert o["directors"] == one(db, "SELECT COUNT(*) FROM directors")
    assert o["accounts"] == one(db, "SELECT COUNT(*) FROM accounts")
    assert o["active_holdings"] == one(db, "SELECT COUNT(*) FROM product_holdings WHERE status='Active'")
    assert o["recorded_annual_turnover_total"] == pytest.approx(
        one(db, "SELECT SUM(recorded_annual_turnover) FROM businesses"))


def test_six_month_total_reconciles_four_ways(db):
    direct = one(db, DIRECT_TOTAL_SQL)
    summary = business_turnover_summary(db)
    assert portfolio_overview(db)["six_month_turnover_total"] == pytest.approx(direct)
    assert turnover_by_month(db)["total_turnover"].sum() == pytest.approx(direct)
    assert summary["six_month_total"].sum() == pytest.approx(direct)
    for dim in ["industry_sector", "province", "segment"]:
        assert turnover_by_dimension(summary, dim)["six_month_total"].sum() == pytest.approx(direct)


def test_months_reported_reconciles(db):
    captured = one(db, "SELECT COUNT(COALESCE(bm_value, system_value)) FROM monthly_turnover")
    assert business_turnover_summary(db)["months_reported"].sum() == captured
    assert portfolio_overview(db)["turnover_months_captured"] == captured


def test_dimension_breakdowns_keep_every_business(db):
    summary = business_turnover_summary(db)
    for dim in ["industry_sector", "province", "segment"]:
        assert turnover_by_dimension(summary, dim)["businesses"].sum() == len(summary)


# ---------- turnover by month ----------
def test_turnover_by_month_shape_and_consistency(db):
    t = turnover_by_month(db)
    assert list(t["month"]) == MONTHS
    n = one(db, "SELECT COUNT(*) FROM businesses")
    assert (t["businesses_total"] == n).all()
    assert ((t["businesses_reporting"] + t["businesses_missing"]) == t["businesses_total"]).all()


# ---------- per-business summary ----------
def test_business_summary_has_one_row_per_business(db):
    s = business_turnover_summary(db)
    assert len(s) == one(db, "SELECT COUNT(*) FROM businesses")
    assert s["business_id"].is_unique


def test_business_summary_calculations_are_consistent(db):
    s = business_turnover_summary(db)
    assert s["months_reported"].between(0, 6).all()
    has_data = s[s["months_reported"] > 0]
    assert (has_data["highest"] >= has_data["lowest"]).all()
    assert (has_data["lowest"] >= 0).all()
    assert ((has_data["monthly_avg"] * has_data["months_reported"]) - has_data["six_month_total"]).abs().max() < 1e-6
    assert has_data["highest_month"].isin(MONTHS).all()
    assert has_data["lowest_month"].isin(MONTHS).all()


def test_annualised_estimate_only_exists_for_complete_six_months(db):
    s = business_turnover_summary(db)
    complete = s["months_reported"] == 6
    assert s.loc[complete, "annualised_estimate"].notna().all()
    assert s.loc[~complete, "annualised_estimate"].isna().all()
    done = s[complete]
    assert (done["annualised_estimate"] - done["six_month_total"] * 2).abs().max() < 1e-6


def test_variance_and_alignment_signal_rules(db):
    s = business_turnover_summary(db)
    both = s[s["annualised_estimate"].notna() & s["recorded_annual_turnover"].notna()]
    expected = (both["annualised_estimate"] / both["recorded_annual_turnover"] - 1) * 100
    assert (both["variance_vs_recorded_pct"] - expected).abs().max() < 1e-6
    limit = ALIGNMENT_THRESHOLD * 100
    above = both["variance_vs_recorded_pct"] > limit
    assert both.loc[above, "alignment_signal"].str.contains("above").all()
    assert (s.loc[~s.index.isin(both.index), "alignment_signal"] == "Cannot compare").all()


def test_bm_values_override_system_values(db):
    row = db.execute("SELECT business_id, month, system_value, bm_value FROM monthly_turnover "
                     "WHERE system_value IS NOT NULL AND bm_value IS NOT NULL LIMIT 1").fetchone()
    business_id, month, system_value, bm_value = row
    total_sql = (f"SELECT SUM(COALESCE(bm_value, system_value)) FROM monthly_turnover WHERE business_id={business_id}")
    s = business_turnover_summary(db)
    assert s.loc[s["business_id"] == business_id, "six_month_total"].iloc[0] == pytest.approx(one(db, total_sql))


# ---------- products and activity ----------
def test_product_penetration(db):
    p = product_penetration(db)
    n = one(db, "SELECT COUNT(*) FROM businesses")
    assert (p["businesses_holding"] <= n).all()
    assert p.loc[p["product_code"] == "BCA", "pct_of_businesses"].iloc[0] >= 90


def test_bm_activity_adds_up_to_all_turnover_rows(db):
    assert bm_activity(db)["months"].sum() == one(db, "SELECT COUNT(*) FROM monthly_turnover")


# ---------- data-quality report ----------
def test_data_quality_report_structure(db):
    r = data_quality_report(db)
    assert list(r.columns) == ["area", "check", "issues", "population", "pct", "severity"]
    assert r["pct"].between(0, 100).all()
    assert set(r["severity"]) <= {"OK", "Low", "Medium", "High"}
    assert (r["issues"] <= r["population"]).all()


def test_data_quality_counts_match_direct_queries(db):
    r = data_quality_report(db).set_index("check")
    assert r.loc["Accounts opened before business established", "issues"] == one(
        db, "SELECT COUNT(*) FROM accounts a JOIN businesses b USING(business_id) "
            "WHERE a.open_date < b.date_established")
    assert r.loc["Province missing", "issues"] == one(db, "SELECT COUNT(*) FROM businesses WHERE province IS NULL")
    assert r.loc["Recorded annual turnover missing", "issues"] == one(
        db, "SELECT COUNT(*) FROM businesses WHERE recorded_annual_turnover IS NULL")
    assert r.loc["Foreign-key violations", "issues"] == 0


def test_data_quality_report_surfaces_the_deliberate_gaps(db):
    r = data_quality_report(db)
    assert (r["issues"] > 0).sum() >= 10
    assert r["issues"].sum() > 0
