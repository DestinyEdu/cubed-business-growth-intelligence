"""Portfolio analytics layer for the Cubed Business Growth Intelligence Lab (PoC).

Pure functions: a database connection goes in, a DataFrame or dict comes out.
ALL DATA IS SYNTHETIC. The annualised turnover figure is an ESTIMATE, not verified annual turnover.
"""
import sqlite3

import pandas as pd

from src.config import DB_PATH

# Illustrative PoC setting: how far the annualised estimate may differ from recorded
# annual turnover before it is flagged as a potential segment-alignment signal.
ALIGNMENT_THRESHOLD = 0.25

EFFECTIVE = "COALESCE(bm_value, system_value)"   # a BM value overrides the system value


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _scalar(conn, sql):
    return conn.execute(sql).fetchone()[0]


def _df(conn, sql):
    return pd.read_sql_query(sql, conn)


# --------------------------------------------------------------------------- overview
def portfolio_overview(conn):
    businesses = _scalar(conn, "SELECT COUNT(*) FROM businesses")
    month_rows = _scalar(conn, "SELECT COUNT(*) FROM monthly_turnover")
    captured = _scalar(conn, f"SELECT COUNT({EFFECTIVE}) FROM monthly_turnover")
    active_holdings = _scalar(conn, "SELECT COUNT(*) FROM product_holdings WHERE status='Active'")
    return {
        "clients": _scalar(conn, "SELECT COUNT(*) FROM client_master"),
        "businesses": businesses,
        "multi_business_clients": _scalar(
            conn, "SELECT COUNT(*) FROM (SELECT client_id FROM businesses GROUP BY 1 HAVING COUNT(*) > 1)"),
        "directors": _scalar(conn, "SELECT COUNT(*) FROM directors"),
        "accounts": _scalar(conn, "SELECT COUNT(*) FROM accounts"),
        "open_accounts": _scalar(conn, "SELECT COUNT(*) FROM accounts WHERE status='Open'"),
        "active_holdings": active_holdings,
        "avg_active_products_per_business": round(active_holdings / businesses, 2),
        "recorded_annual_turnover_total": _scalar(
            conn, "SELECT COALESCE(SUM(recorded_annual_turnover), 0) FROM businesses"),
        "businesses_with_recorded_turnover": _scalar(
            conn, "SELECT COUNT(recorded_annual_turnover) FROM businesses"),
        "six_month_turnover_total": _scalar(
            conn, f"SELECT COALESCE(SUM({EFFECTIVE}), 0) FROM monthly_turnover"),
        "turnover_months_expected": month_rows,
        "turnover_months_captured": captured,
        "turnover_completeness_pct": round(100 * captured / month_rows, 1) if month_rows else 0.0,
    }


# --------------------------------------------------------------------------- turnover trends
def turnover_by_month(conn):
    df = _df(conn, f"""
        SELECT month,
               COALESCE(SUM({EFFECTIVE}), 0)            AS total_turnover,
               COUNT({EFFECTIVE})                        AS businesses_reporting,
               SUM(value_source = 'MISSING')             AS businesses_missing,
               SUM(value_source = 'BM')                  AS bm_captured_or_corrected,
               COUNT(*)                                  AS businesses_total
        FROM monthly_turnover GROUP BY month ORDER BY month""")
    # The average per reporting business is a fairer trend measure than the raw total,
    # because the number of businesses reporting changes from month to month.
    df["avg_per_reporting_business"] = df["total_turnover"] / df["businesses_reporting"]
    df["total_mom_pct"] = df["total_turnover"].pct_change() * 100
    df["avg_mom_pct"] = df["avg_per_reporting_business"].pct_change() * 100
    return df


def business_turnover_summary(conn):
    """One row per business: the six-month calculations from the PoC specification."""
    biz = _df(conn, """
        SELECT b.business_id, m.cun, b.business_name, b.industry_sector, b.province,
               m.segment, b.recorded_annual_turnover
        FROM businesses b JOIN client_master m ON m.client_id = b.client_id""")
    long = _df(conn, f"SELECT business_id, month, {EFFECTIVE} AS eff FROM monthly_turnover").dropna(subset=["eff"])

    g = long.groupby("business_id")["eff"]
    agg = pd.DataFrame({"six_month_total": g.sum(), "months_reported": g.count(), "monthly_avg": g.mean(),
                        "highest": g.max(), "lowest": g.min()})
    agg["highest_month"] = long.loc[g.idxmax()].set_index("business_id")["month"]
    agg["lowest_month"] = long.loc[g.idxmin()].set_index("business_id")["month"]

    pivot = long.pivot(index="business_id", columns="month", values="eff")
    months = sorted(pivot.columns)
    agg["latest_mom_pct"] = (pivot[months[-1]] / pivot[months[-2]] - 1) * 100

    out = biz.merge(agg, left_on="business_id", right_index=True, how="left")
    out["months_reported"] = out["months_reported"].fillna(0).astype(int)

    # ESTIMATE only, and only when all six months are available
    out["annualised_estimate"] = out["six_month_total"].where(out["months_reported"] == 6) * 2
    out["variance_vs_recorded_pct"] = (out["annualised_estimate"] / out["recorded_annual_turnover"] - 1) * 100

    def flag(row):
        v = row["variance_vs_recorded_pct"]
        if pd.isna(v):
            return "Cannot compare"
        if v > ALIGNMENT_THRESHOLD * 100:
            return "Estimate well above recorded: review segment alignment"
        if v < -ALIGNMENT_THRESHOLD * 100:
            return "Estimate well below recorded: review"
        return "Broadly aligned"

    out["alignment_signal"] = out.apply(flag, axis=1)
    return out


def turnover_by_dimension(summary, dim):
    """Break the per-business summary down by e.g. 'industry_sector', 'province' or 'segment'."""
    d = summary.copy()
    d[dim] = d[dim].fillna("(missing)")
    out = d.groupby(dim).agg(
        businesses=("business_id", "count"),
        six_month_total=("six_month_total", "sum"),
        months_reported=("months_reported", "sum"),
        recorded_annual_turnover=("recorded_annual_turnover", "sum"),
    ).reset_index()
    out["avg_monthly_per_business"] = out["six_month_total"] / out["months_reported"].replace(0, pd.NA)
    return out.sort_values("six_month_total", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- products
def product_penetration(conn):
    total = _scalar(conn, "SELECT COUNT(*) FROM businesses")
    df = _df(conn, """
        SELECT product_code, product_name, COUNT(DISTINCT business_id) AS businesses_holding
        FROM product_holdings WHERE status = 'Active'
        GROUP BY product_code, product_name ORDER BY businesses_holding DESC""")
    df["pct_of_businesses"] = (100 * df["businesses_holding"] / total).round(1)
    return df


# --------------------------------------------------------------------------- data quality
def _severity(pct):
    if pct == 0:
        return "OK"
    if pct >= 10:
        return "High"
    if pct >= 5:
        return "Medium"
    return "Low"


def data_quality_report(conn):
    """Counts every data-quality issue, with the population it is measured against."""
    checks = []

    def missing(area, table, column, label):
        checks.append((area, f"{label} missing",
                       f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL", f"SELECT COUNT(*) FROM {table}"))

    missing("Clients", "client_master", "segment", "Segment")
    for col, label in [("entity_type", "Entity type"), ("industry_sector", "Industry sector"),
                       ("province", "Province"), ("date_established", "Date established"),
                       ("employee_count", "Employee count"),
                       ("recorded_annual_turnover", "Recorded annual turnover")]:
        missing("Businesses", "businesses", col, label)
    missing("Directors", "directors", "role", "Director role")
    missing("Directors", "directors", "id_category", "ID category")
    missing("Accounts", "accounts", "account_type", "Account type")
    missing("Accounts", "accounts", "open_date", "Account open date")
    missing("Product holdings", "product_holdings", "start_date", "Holding start date")

    checks += [
        ("Accounts", "Accounts opened before business established",
         "SELECT COUNT(*) FROM accounts a JOIN businesses b ON b.business_id=a.business_id "
         "WHERE a.open_date < b.date_established",
         "SELECT COUNT(*) FROM accounts"),
        ("Turnover", "Businesses with at least one missing month",
         f"SELECT COUNT(*) FROM (SELECT business_id FROM monthly_turnover GROUP BY 1 "
         f"HAVING COUNT({EFFECTIVE}) < 6)",
         "SELECT COUNT(*) FROM businesses"),
        ("Turnover", "Businesses with no turnover for any month",
         f"SELECT COUNT(*) FROM (SELECT business_id FROM monthly_turnover GROUP BY 1 "
         f"HAVING COUNT({EFFECTIVE}) = 0)",
         "SELECT COUNT(*) FROM businesses"),
        ("Conduct", "Accounts with 3+ returned debit orders and no BM explanation",
         "SELECT COUNT(*) FROM account_conduct WHERE returned_debit_orders >= 3 AND bm_explanation IS NULL",
         "SELECT COUNT(*) FROM account_conduct WHERE returned_debit_orders >= 3"),
        ("Integrity", "Foreign-key violations",
         "SELECT COUNT(*) FROM pragma_foreign_key_check",
         "SELECT (SELECT COUNT(*) FROM businesses) + (SELECT COUNT(*) FROM accounts) "
         "+ (SELECT COUNT(*) FROM product_holdings) + (SELECT COUNT(*) FROM monthly_turnover)"),
    ]

    rows = []
    for area, check, issue_sql, pop_sql in checks:
        issues, population = _scalar(conn, issue_sql), _scalar(conn, pop_sql)
        pct = round(100 * issues / population, 1) if population else 0.0
        rows.append({"area": area, "check": check, "issues": issues, "population": population,
                     "pct": pct, "severity": _severity(pct)})
    return pd.DataFrame(rows)


def bm_activity(conn):
    """How much of the turnover data the Business Managers have captured or corrected."""
    return _df(conn, """
        SELECT value_source, COUNT(*) AS months FROM monthly_turnover GROUP BY value_source ORDER BY months DESC""")
