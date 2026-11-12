"""
Cubed Business Growth Intelligence Lab
Portfolio Intelligence Dashboard

Proof of Concept - Synthetic Data Only.
"""

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================================================
# 1. PROJECT CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.analytics import (
    connect,
    portfolio_overview,
    business_turnover_summary,
    turnover_by_month,
    data_quality_report,
    bm_activity,
)


st.set_page_config(
    page_title="Cubed | Business Growth Intelligence",
    page_icon="📊",
    layout="wide",
)


# =========================================================
# 2. APPLICATION HEADER
# =========================================================

st.title("Cubed Business Growth Intelligence")

st.caption(
    "Portfolio Intelligence Dashboard | "
    "Proof of Concept | Synthetic Data Only"
)


# =========================================================
# 3. HELPER FUNCTIONS
# =========================================================

def format_rand(value):

    if pd.isna(value):
        return "N/A"

    return f"R {value:,.0f}"


def format_percentage(value):

    if pd.isna(value):
        return "N/A"

    return f"{value:.2f}%"


# =========================================================
# 4. LOAD PORTFOLIO DATA
# =========================================================

@st.cache_data(ttl=60)
def load_dashboard_data():

    conn = connect()

    try:

        overview = portfolio_overview(conn)

        business_summary = business_turnover_summary(conn)

        monthly = turnover_by_month(conn)

        segments = pd.read_sql_query(
            """
            SELECT
                COALESCE(
                    segment,
                    'Missing / Not captured'
                ) AS segment,
                COUNT(*) AS clients
            FROM client_master
            GROUP BY segment
            ORDER BY clients DESC
            """,
            conn,
        )

        return (
            overview,
            business_summary,
            monthly,
            segments,
        )

    finally:
        conn.close()


# =========================================================
# 5. LOAD DATA QUALITY DATA
# =========================================================

@st.cache_data(ttl=60)
def load_quality_data():

    conn = connect()

    try:

        quality = data_quality_report(conn)

        activity = bm_activity(conn)

        return quality, activity

    finally:
        conn.close()


(
    overview,
    business_summary,
    monthly,
    segments,
) = load_dashboard_data()


quality_report, activity_report = load_quality_data()


# =========================================================
# 6. SIDEBAR NAVIGATION
# =========================================================

st.sidebar.title("Portfolio Navigation")

st.sidebar.info(
    """
    **Current module**

    Portfolio Overview

    Additional modules will be introduced
    in subsequent development milestones.
    """
)


if st.sidebar.button("Refresh dashboard"):

    st.cache_data.clear()

    st.rerun()


st.sidebar.markdown("---")

st.sidebar.caption(
    "Cubed Digital Labs | Business Intelligence"
)


# =========================================================
# 7. PORTFOLIO FILTERS
# =========================================================

st.sidebar.markdown("---")

st.sidebar.subheader("Portfolio Filters")


filter_data = business_summary.copy()


filter_data["segment"] = (
    filter_data["segment"]
    .fillna("Missing / Not captured")
)

filter_data["industry_sector"] = (
    filter_data["industry_sector"]
    .fillna("Missing / Not captured")
)

filter_data["province"] = (
    filter_data["province"]
    .fillna("Missing / Not captured")
)

filter_data["alignment_signal"] = (
    filter_data["alignment_signal"]
    .fillna("Missing / Not assessed")
)


# Segment

segment_options = sorted(
    filter_data["segment"].unique()
)

selected_segments = st.sidebar.multiselect(
    "Select segment",
    options=segment_options,
    default=segment_options,
)


# Industry

industry_options = sorted(
    filter_data["industry_sector"].unique()
)

selected_industries = st.sidebar.multiselect(
    "Select industry",
    options=industry_options,
    default=industry_options,
)


# Province

province_options = sorted(
    filter_data["province"].unique()
)

selected_provinces = st.sidebar.multiselect(
    "Select province",
    options=province_options,
    default=province_options,
)


# Turnover alignment

alignment_options = sorted(
    filter_data["alignment_signal"].unique()
)

selected_alignment = st.sidebar.multiselect(
    "Turnover alignment",
    options=alignment_options,
    default=alignment_options,
)


# Business search

business_search = st.sidebar.text_input(
    "Search business name or CUN"
)


# Apply filters

filtered_business_summary = filter_data[
    filter_data["segment"].isin(selected_segments)
    & filter_data["industry_sector"].isin(selected_industries)
    & filter_data["province"].isin(selected_provinces)
    & filter_data["alignment_signal"].isin(selected_alignment)
].copy()


if business_search.strip():

    search_term = business_search.strip().lower()

    name_match = (
        filtered_business_summary["business_name"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(search_term, regex=False)
    )

    cun_match = (
        filtered_business_summary["cun"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(search_term, regex=False)
    )

    filtered_business_summary = (
        filtered_business_summary[
            name_match | cun_match
        ]
    )


st.sidebar.caption(
    f"Businesses matching filters: "
    f"{len(filtered_business_summary):,}"
)


# =========================================================
# 8. PORTFOLIO OVERVIEW
# =========================================================

st.markdown("---")

st.subheader("Portfolio Overview")


col1, col2, col3, col4, col5 = st.columns(5)


col1.metric(
    "Client Relationships",
    f"{overview['clients']:,}",
)

col2.metric(
    "Businesses",
    f"{overview['businesses']:,}",
)

col3.metric(
    "Total Accounts",
    f"{overview['accounts']:,}",
)

col4.metric(
    "Open Accounts",
    f"{overview['open_accounts']:,}",
)

col5.metric(
    "Active Product Holdings",
    f"{overview['active_holdings']:,}",
)


# =========================================================
# 9. FINANCIAL OVERVIEW
# =========================================================

st.markdown("---")

st.subheader("Financial Overview")


col1, col2, col3, col4 = st.columns(4)


col1.metric(
    "Recorded Annual Turnover",
    format_rand(
        overview["recorded_annual_turnover_total"]
    ),
)

col2.metric(
    "Six-Month Turnover",
    format_rand(
        overview["six_month_turnover_total"]
    ),
)

col3.metric(
    "Average Active Products / Business",
    f"{overview['avg_active_products_per_business']:.2f}",
)

col4.metric(
    "Turnover Data Completeness",
    f"{overview['turnover_completeness_pct']:.1f}%",
)


st.caption(
    "Financial overview indicators represent the entire portfolio "
    "and are not affected by the sidebar filters."
)


# =========================================================
# 10. PORTFOLIO COMPOSITION
# =========================================================

st.markdown("---")

st.subheader("Portfolio Composition")


st.metric(
    "Businesses in Current View",
    f"{len(filtered_business_summary):,}",
)


if not filtered_business_summary.empty:

    sector_data = (
        filtered_business_summary
        .groupby("industry_sector")
        .size()
        .reset_index(name="businesses")
        .sort_values("businesses", ascending=False)
    )

    province_data = (
        filtered_business_summary
        .groupby("province")
        .size()
        .reset_index(name="businesses")
        .sort_values("businesses", ascending=False)
    )

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            "**Businesses by Industry Sector**"
        )

        fig_sector = px.bar(
            sector_data,
            x="businesses",
            y="industry_sector",
            orientation="h",
            text="businesses",
            color="businesses",
            color_continuous_scale="Blues",
        )

        fig_sector.update_layout(
            yaxis={
                "categoryorder": "total ascending"
            },
            xaxis_title="Number of Businesses",
            yaxis_title="",
            coloraxis_showscale=False,
            height=450,
        )

        st.plotly_chart(
            fig_sector,
            use_container_width=True,
        )

    with col2:

        st.markdown(
            "**Businesses by Province**"
        )

        fig_province = px.bar(
            province_data,
            x="businesses",
            y="province",
            orientation="h",
            text="businesses",
            color="businesses",
            color_continuous_scale="Teal",
        )

        fig_province.update_layout(
            yaxis={
                "categoryorder": "total ascending"
            },
            xaxis_title="Number of Businesses",
            yaxis_title="",
            coloraxis_showscale=False,
            height=450,
        )

        st.plotly_chart(
            fig_province,
            use_container_width=True,
        )

else:

    st.warning(
        "No businesses match the selected filters."
    )


# Client segment distribution

st.markdown(
    "**Client Relationships by Segment – Entire Portfolio**"
)

st.caption(
    "This chart represents all client relationships, "
    "independent of business filters."
)


fig_segment = px.pie(
    segments,
    names="segment",
    values="clients",
    hole=0.45,
)

fig_segment.update_traces(
    textposition="inside",
    textinfo="percent+label",
)

fig_segment.update_layout(
    height=400,
)

st.plotly_chart(
    fig_segment,
    use_container_width=True,
)


# =========================================================
# 11. FINANCIAL PERFORMANCE AND TURNOVER INTELLIGENCE
# =========================================================

st.markdown("---")

st.subheader(
    "Financial Performance and Turnover Intelligence"
)


monthly = monthly.sort_values("month").copy()


if not monthly.empty:

    latest_month = monthly.iloc[-1]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Latest Monthly Turnover",
        format_rand(
            latest_month["total_turnover"]
        ),
        delta=(
            format_percentage(
                latest_month["total_mom_pct"]
            )
            if pd.notna(
                latest_month["total_mom_pct"]
            )
            else None
        ),
    )

    col2.metric(
        "Businesses Reporting",
        f"{int(latest_month['businesses_reporting']):,}",
    )

    col3.metric(
        "Businesses Missing Turnover",
        f"{int(latest_month['businesses_missing']):,}",
    )

    col4.metric(
        "Average Turnover per Reporting Business",
        format_rand(
            latest_month[
                "avg_per_reporting_business"
            ]
        ),
    )

    st.caption(
        f"Latest reporting month: {latest_month['month']}. "
        "Movement compares the latest month with the preceding month."
    )

    st.markdown("---")


    # Monthly turnover trend

    st.markdown(
        "### 1. Monthly Turnover Trend"
    )

    fig_turnover = px.line(
        monthly,
        x="month",
        y="total_turnover",
        markers=True,
        title="Total Monthly Portfolio Turnover",
    )

    fig_turnover.update_layout(
        xaxis_title="Month",
        yaxis_title="Turnover (R)",
        hovermode="x unified",
    )

    st.plotly_chart(
        fig_turnover,
        use_container_width=True,
    )


    # Reporting coverage

    st.markdown(
        "### 2. Monthly Turnover Reporting Coverage"
    )

    coverage_data = monthly.melt(
        id_vars=["month"],
        value_vars=[
            "businesses_reporting",
            "businesses_missing",
        ],
        var_name="reporting_status",
        value_name="business_count",
    )

    coverage_data["reporting_status"] = (
        coverage_data["reporting_status"].map(
            {
                "businesses_reporting": "Reporting",
                "businesses_missing": "Missing",
            }
        )
    )

    fig_coverage = px.bar(
        coverage_data,
        x="month",
        y="business_count",
        color="reporting_status",
        barmode="group",
        text="business_count",
        title="Businesses Reporting vs Missing Turnover",
    )

    fig_coverage.update_layout(
        xaxis_title="Month",
        yaxis_title="Number of Businesses",
    )

    st.plotly_chart(
        fig_coverage,
        use_container_width=True,
    )


    # Month-on-month movement

    st.markdown(
        "### 3. Month-on-Month Turnover Movement"
    )

    mom_data = monthly.dropna(
        subset=["total_mom_pct"]
    )

    if not mom_data.empty:

        fig_mom = px.bar(
            mom_data,
            x="month",
            y="total_mom_pct",
            text_auto=".2f",
            title="Monthly Turnover Growth / Decline (%)",
        )

        fig_mom.add_hline(
            y=0,
            line_dash="dash",
        )

        fig_mom.update_layout(
            xaxis_title="Month",
            yaxis_title="Movement (%)",
        )

        st.plotly_chart(
            fig_mom,
            use_container_width=True,
        )

    else:

        st.info(
            "Month-on-month movement is not available yet."
        )


    # Monthly performance table

    st.markdown(
        "### 4. Monthly Financial Performance"
    )

    monthly_display = monthly[
        [
            "month",
            "total_turnover",
            "businesses_reporting",
            "businesses_missing",
            "bm_captured_or_corrected",
            "avg_per_reporting_business",
            "total_mom_pct",
            "avg_mom_pct",
        ]
    ].copy()

    monthly_display = monthly_display.rename(
        columns={
            "month": "Month",
            "total_turnover": "Total Turnover",
            "businesses_reporting": "Businesses Reporting",
            "businesses_missing": "Businesses Missing",
            "bm_captured_or_corrected": "BM Captured / Corrected",
            "avg_per_reporting_business": "Average Turnover per Business",
            "total_mom_pct": "Total Turnover Movement (%)",
            "avg_mom_pct": "Average Turnover Movement (%)",
        }
    )

    st.dataframe(
        monthly_display,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.warning(
        "No monthly turnover records are available."
    )


# =========================================================
# 12. TURNOVER DATA CAPTURE
# =========================================================

st.markdown("---")

st.subheader("Turnover Data Capture")


col1, col2 = st.columns(2)


with col1:

    st.metric(
        "Expected Monthly Records",
        f"{overview['turnover_months_expected']:,}",
    )

    st.metric(
        "Captured Monthly Records",
        f"{overview['turnover_months_captured']:,}",
    )


with col2:

    completeness = overview["turnover_completeness_pct"]

    st.progress(
        min(
            max(completeness / 100, 0.0),
            1.0,
        )
    )

    st.write(
        f"**{completeness:.1f}%** "
        "of expected turnover records have values."
    )


# =========================================================
# 13. BUSINESS PORTFOLIO SUMMARY
# =========================================================

st.markdown("---")

st.subheader("Business Portfolio Summary")


display_columns = [
    "cun",
    "business_name",
    "industry_sector",
    "province",
    "segment",
    "recorded_annual_turnover",
    "six_month_total",
    "months_reported",
    "annualised_estimate",
    "variance_vs_recorded_pct",
    "alignment_signal",
]


display_data = filtered_business_summary[
    display_columns
].copy()


display_data = display_data.rename(
    columns={
        "cun": "CUN",
        "business_name": "Business Name",
        "industry_sector": "Industry Sector",
        "province": "Province",
        "segment": "Segment",
        "recorded_annual_turnover": "Recorded Annual Turnover",
        "six_month_total": "Six-Month Turnover",
        "months_reported": "Months Reported",
        "annualised_estimate": "Annualised Estimate",
        "variance_vs_recorded_pct": "Variance vs Recorded (%)",
        "alignment_signal": "Alignment Signal",
    }
)


st.dataframe(
    display_data,
    use_container_width=True,
    hide_index=True,
)


st.info(
    """
    **Turnover interpretation**

    - Annualised estimates are calculated only when all six months
      of turnover data are available.
    - Variance compares the annualised estimate against recorded
      annual turnover.
    - Significant deviations are flagged for further BM investigation.
    - Businesses with incomplete turnover data remain visible.
    - These indicators are prompts for client engagement, not
      verified financial statements or credit decisions.
    """
)


# =========================================================
# 14. DATA QUALITY AND BM ACTION INTELLIGENCE
# =========================================================

st.markdown("---")

st.subheader(
    "Data Quality and BM Action Intelligence"
)

st.caption(
    "Identifies missing, incomplete or inconsistent information "
    "that may require Business Manager attention."
)


# ---------------------------------------------------------
# 14.1 DATA QUALITY SUMMARY
# ---------------------------------------------------------

total_issue_instances = int(
    quality_report["issues"].sum()
)

high_issues = int(
    quality_report.loc[
        quality_report["severity"] == "High",
        "issues",
    ].sum()
)

medium_issues = int(
    quality_report.loc[
        quality_report["severity"] == "Medium",
        "issues",
    ].sum()
)

low_issues = int(
    quality_report.loc[
        quality_report["severity"] == "Low",
        "issues",
    ].sum()
)

ok_checks = int(
    (quality_report["severity"] == "OK").sum()
)


col1, col2, col3, col4, col5 = st.columns(5)


col1.metric(
    "Issue Instances",
    f"{total_issue_instances:,}",
)

col2.metric(
    "High Severity",
    f"{high_issues:,}",
)

col3.metric(
    "Medium Severity",
    f"{medium_issues:,}",
)

col4.metric(
    "Low Severity",
    f"{low_issues:,}",
)

col5.metric(
    "Checks Passed",
    f"{ok_checks:,}",
)


st.caption(
    "Issue instances are counts across individual checks. "
    "A single record may contribute to multiple checks. "
    "These are not unique affected-client counts."
)


# ---------------------------------------------------------
# 14.2 SEVERITY DISTRIBUTION
# ---------------------------------------------------------

st.markdown(
    "### 1. Data Quality Severity Distribution"
)


severity_summary = (
    quality_report
    .groupby("severity", as_index=False)
    .agg(
        issue_instances=("issues", "sum"),
        checks=("check", "count"),
    )
)


severity_order = [
    "High",
    "Medium",
    "Low",
    "OK",
]


severity_summary["severity"] = pd.Categorical(
    severity_summary["severity"],
    categories=severity_order,
    ordered=True,
)


severity_summary = severity_summary.sort_values(
    "severity"
)


fig_severity = px.bar(
    severity_summary,
    x="severity",
    y="issue_instances",
    text="issue_instances",
    title="Issue Instances by Severity",
)


fig_severity.update_layout(
    xaxis_title="Severity",
    yaxis_title="Issue Instances",
)


st.plotly_chart(
    fig_severity,
    use_container_width=True,
)


# ---------------------------------------------------------
# 14.3 DATA QUALITY BY AREA
# ---------------------------------------------------------

st.markdown(
    "### 2. Data Quality by Business Area"
)


area_summary = (
    quality_report
    .groupby("area", as_index=False)
    .agg(
        issue_instances=("issues", "sum"),
        checks=("check", "count"),
    )
    .sort_values(
        "issue_instances",
        ascending=False,
    )
)


fig_area = px.bar(
    area_summary,
    x="issue_instances",
    y="area",
    orientation="h",
    text="issue_instances",
    title="Issue Instances by Data Area",
)


fig_area.update_layout(
    yaxis={
        "categoryorder": "total ascending"
    },
    xaxis_title="Issue Instances",
    yaxis_title="",
)


st.plotly_chart(
    fig_area,
    use_container_width=True,
)


# ---------------------------------------------------------
# 14.4 DETAILED QUALITY REPORT
# ---------------------------------------------------------

st.markdown(
    "### 3. Detailed Data Quality Report"
)


quality_display = quality_report[
    [
        "area",
        "check",
        "issues",
        "population",
        "pct",
        "severity",
    ]
].copy()


quality_display = quality_display.rename(
    columns={
        "area": "Data Area",
        "check": "Quality Check",
        "issues": "Issues Found",
        "population": "Population Checked",
        "pct": "Issue Rate (%)",
        "severity": "Severity",
    }
)


st.dataframe(
    quality_display,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# 14.5 TURNOVER FOLLOW-UP
# ---------------------------------------------------------

st.markdown(
    "### 4. Businesses Requiring Turnover Follow-up"
)


st.caption(
    "Businesses with fewer than six reported months "
    "are highlighted for possible data capture or client engagement."
)


turnover_follow_up = business_summary[
    business_summary["months_reported"] < 6
].copy()


turnover_follow_up = turnover_follow_up.sort_values(
    by=["months_reported", "business_name"],
    ascending=[True, True],
)


st.metric(
    "Businesses with Incomplete Turnover",
    f"{len(turnover_follow_up):,}",
)


if not turnover_follow_up.empty:

    follow_up_columns = [
        "cun",
        "business_name",
        "industry_sector",
        "province",
        "recorded_annual_turnover",
        "six_month_total",
        "months_reported",
        "alignment_signal",
    ]


    follow_up_display = turnover_follow_up[
        follow_up_columns
    ].copy()


    follow_up_display = follow_up_display.rename(
        columns={
            "cun": "CUN",
            "business_name": "Business Name",
            "industry_sector": "Industry Sector",
            "province": "Province",
            "recorded_annual_turnover": "Recorded Annual Turnover",
            "six_month_total": "Six-Month Turnover",
            "months_reported": "Months Reported",
            "alignment_signal": "Alignment Signal",
        }
    )


    st.dataframe(
        follow_up_display,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.success(
        "All businesses have six months of reported turnover."
    )


# ---------------------------------------------------------
# 14.6 BM DATA CAPTURE CONTRIBUTION
# ---------------------------------------------------------

st.markdown(
    "### 5. Business Manager Data Capture Contribution"
)


st.caption(
    "Distribution of monthly turnover records according "
    "to their recorded value source."
)


if not activity_report.empty:

    fig_activity = px.bar(
        activity_report,
        x="value_source",
        y="months",
        text="months",
        title="Turnover Records by Value Source",
    )


    fig_activity.update_layout(
        xaxis_title="Value Source",
        yaxis_title="Number of Monthly Records",
    )


    st.plotly_chart(
        fig_activity,
        use_container_width=True,
    )


    st.dataframe(
        activity_report,
        use_container_width=True,
        hide_index=True,
    )

else:

    st.info(
        "No Business Manager turnover activity records are available."
    )


# ---------------------------------------------------------
# 14.7 BM ACTION GUIDANCE
# ---------------------------------------------------------

st.markdown(
    "### 6. Suggested Business Manager Actions"
)


st.info(
    """
    **Recommended follow-up priorities**

    1. Incomplete turnover:
       Contact the client or review available information
       to complete missing monthly turnover records.

    2. Missing business information:
       Capture missing industry, province, entity type
       and other relevant business details.

    3. Account information inconsistencies:
       Investigate account dates that appear earlier
       than the business establishment date.

    4. Returned debit orders:
       Obtain and record an explanation where three or more
       returned debit orders have no BM explanation.

    5. Referential integrity:
       Escalate foreign-key violations to the appropriate
       data or platform administrator.

    6. BM data capture:
       Review the balance between system-sourced and
       BM-captured or corrected turnover records.
    """
)


st.caption(
    "Data-quality indicators support information remediation "
    "and portfolio management. They are not credit-risk scores, "
    "fraud determinations or lending decisions."
)


# =========================================================
# 15. FOOTER
# =========================================================

st.markdown("---")


st.caption(
    "Cubed Digital Labs | "
    "Cubed Business Growth Intelligence Lab"
)


st.caption(
    "All figures are synthetic and intended for demonstration "
    "purposes. Annualised turnover is an estimate, not verified "
    "annual turnover. This application is not connected to "
    "live banking systems."
)
