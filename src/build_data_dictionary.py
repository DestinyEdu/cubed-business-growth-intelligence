"""Builds docs/data_dictionary.md from the live database schema (synthetic PoC)."""
import sqlite3

from src.config import DB_PATH, PROJECT_ROOT

OUTPUT = PROJECT_ROOT / "docs" / "data_dictionary.md"

PURPOSE = {
    "client_master": "CUN and core client information.",
    "businesses": "Business profiles and entity details. One CUN can link to several businesses.",
    "directors": "Directors, proprietors and identification categories.",
    "accounts": "Client accounts and account-level information. Attached to a business, never to the CUN.",
    "product_holdings": "Existing products and services held by a business.",
    "monthly_turnover": "Six monthly turnover records, with the system value and any BM correction held side by side.",
    "account_conduct": "Returned debit orders for an account, with return reasons and the BM explanation.",
    "product_recommendations": "Eligibility, take-up score, ranking and reason codes per product and business.",
    "product_rules": "Configurable, versioned product eligibility and scoring rules.",
    "discussion_assists": "Approved product scripts and the AI-enhanced discussion guides built from them.",
    "client_engagements": "BM notes, client responses and agreed actions.",
    "crm_pipeline": "Opportunities, stages, handovers and outcomes.",
    "users": "Simulated Business Manager and management users.",
    "audit_logs": "Changes, timestamps, user actions and rule versions.",
}

DESCRIPTIONS = {
    "users": {
        "user_id": "Unique user identifier.",
        "username": "Simulated login name (unique).",
        "full_name": "Fictional name.",
        "role": "RBAC role: Business Manager, Area Manager, MIS Analyst, Product Owner, Compliance and Audit or System Admin.",
        "area": "Area for Business Managers and Area Managers; empty for central roles.",
        "is_active": "1 = active, 0 = inactive.",
    },
    "client_master": {
        "client_id": "Internal identifier.",
        "cun": "Synthetic Customer Unique Number, format SYN-000000 (unique).",
        "client_name": "Name of the client's primary business.",
        "segment": "Illustrative PoC segment band (Micro, Small, Medium, Large SME) derived from turnover. May be missing.",
        "relationship_start": "Date the client relationship began (ISO date).",
        "assigned_bm_id": "Business Manager responsible for the client.",
        "status": "Active or Dormant.",
        "is_synthetic": "Always 1. The database rejects any other value.",
    },
    "businesses": {
        "business_id": "Internal identifier.",
        "client_id": "The client (CUN) this business belongs to.",
        "business_name": "Fictional business name.",
        "entity_type": "Private company, close corporation, sole proprietor, partnership or trust. May be missing.",
        "industry_sector": "Industry sector. May be missing.",
        "province": "South African province. May be missing.",
        "date_established": "Date the business was established (ISO date). May be missing.",
        "employee_count": "Number of employees. May be missing.",
        "recorded_annual_turnover": "Recorded annual turnover in rand. Not verified. May be missing.",
        "status": "Business status.",
    },
    "directors": {
        "director_id": "Internal identifier.",
        "business_id": "The business the director or proprietor belongs to.",
        "full_name": "Fictional name.",
        "role": "Director, Member, Trustee, Partner or Proprietor. May be missing.",
        "id_category": "Identification category only (never an ID number). May be missing.",
    },
    "accounts": {
        "account_id": "Internal identifier.",
        "business_id": "The business that owns the account.",
        "account_ref": "Synthetic account reference, format SYN-ACC-######## (unique).",
        "account_type": "Cheque, savings or notice deposit. May be missing.",
        "open_date": "Date the account was opened (ISO date). May be missing.",
        "status": "Open, Dormant or Closed.",
    },
    "product_holdings": {
        "holding_id": "Internal identifier.",
        "business_id": "The business holding the product.",
        "account_id": "Linked account where the product is account-based. May be empty.",
        "product_code": "Code from the illustrative product catalogue.",
        "product_name": "Name from the illustrative product catalogue.",
        "start_date": "Date the product started (ISO date). May be missing.",
        "status": "Active or Closed.",
    },
    "monthly_turnover": {
        "turnover_id": "Internal identifier.",
        "business_id": "The business the turnover belongs to.",
        "account_id": "Cheque account the turnover relates to.",
        "month": "Month in YYYY-MM format. One row per business per month.",
        "system_value": "System pre-populated turnover in rand. Empty if none was available.",
        "bm_value": "Value captured or corrected by the Business Manager. The system value is retained alongside it.",
        "value_source": "SYSTEM, BM or MISSING.",
        "captured_by": "Business Manager who captured or corrected the value.",
        "captured_at": "Date of the BM capture or correction.",
    },
    "account_conduct": {
        "conduct_id": "Internal identifier.",
        "account_id": "The account the conduct relates to.",
        "period_end": "End date of the six-month conduct window.",
        "returned_debit_orders": "Number of returned debit orders in the six months.",
        "return_reasons": "Semicolon-separated return reasons. Empty when there are no returns.",
        "bm_explanation": "Client explanation recorded by the BM. Required for 3 or more returns.",
        "recorded_by": "Business Manager who recorded the explanation.",
        "recorded_at": "Date the explanation was recorded.",
    },
    "product_rules": {
        "rule_id": "Internal identifier.",
        "product_code": "Product the rule applies to.",
        "rule_name": "Short rule name.",
        "rule_type": "ELIGIBILITY or SCORING.",
        "parameters": "Rule definition (JSON text).",
        "points": "Points awarded when a scoring rule applies.",
        "version": "Rule version, recorded for audit.",
        "approval_status": "DRAFT, APPROVED or RETIRED.",
        "drafted_by": "Product Owner who drafted the rule.",
        "approved_by": "Compliance and Audit approver. Must differ from drafted_by.",
    },
    "product_recommendations": {
        "recommendation_id": "Internal identifier.",
        "business_id": "The business the recommendation is for.",
        "product_code": "Product being evaluated.",
        "take_up_score": "Estimated commercial take-up potential, 0 to 5. Not creditworthiness.",
        "eligibility_status": "ELIGIBLE, ELIGIBLE_WITH_CONDITIONS or DISQUALIFIED. A disqualified product must score 0.",
        "rank_position": "Rank among the business's products by take-up likelihood.",
        "reason_codes": "Plain-language reasons behind the score and eligibility.",
        "rule_version": "Rule version used to produce the score.",
        "generated_at": "When the recommendation was generated.",
    },
    "discussion_assists": {
        "assist_id": "Internal identifier.",
        "product_code": "Product the script belongs to.",
        "recommendation_id": "Recommendation the guide was built for.",
        "approved_script": "Approved product script text.",
        "ai_enhanced_guide": "Client-specific guide built from the approved script.",
        "script_version": "Script version.",
        "approval_status": "DRAFT, APPROVED or RETIRED.",
        "approved_by": "Approver of the script.",
        "created_at": "When the record was created.",
    },
    "client_engagements": {
        "engagement_id": "Internal identifier.",
        "business_id": "The business discussed.",
        "user_id": "Business Manager who recorded the engagement.",
        "recommendation_id": "Recommendation discussed, if any.",
        "engagement_date": "Date of the conversation.",
        "notes": "BM notes.",
        "client_response": "The client's response.",
        "agreed_action": "Action agreed with the client.",
    },
    "crm_pipeline": {
        "opportunity_id": "Internal identifier.",
        "business_id": "The business the opportunity is for.",
        "engagement_id": "Engagement the opportunity came from.",
        "product_code": "Product in the opportunity.",
        "stage": "Identified, Contacted, Discussed, Interested, Referred or Handed over.",
        "owner_user_id": "Current owner of the opportunity.",
        "next_followup_date": "Date of the next follow-up.",
        "handover_to": "User the opportunity was handed over to.",
        "outcome": "Won, Lost or Deferred. Empty while the opportunity is open.",
        "created_at": "When the opportunity was created.",
        "updated_at": "When the opportunity was last updated.",
    },
    "audit_logs": {
        "log_id": "Internal identifier.",
        "logged_at": "Timestamp of the action.",
        "user_id": "User who performed the action.",
        "table_name": "Table affected.",
        "record_id": "Record affected.",
        "action": "INSERT, UPDATE, DELETE or VIEW.",
        "old_value": "Value before the change.",
        "new_value": "Value after the change.",
        "rule_version": "Rule version in force at the time.",
    },
}

BUSINESS_RULES = [
    "Every client is synthetic: `is_synthetic` must be 1.",
    "`take_up_score` is between 0 and 5. A product with `eligibility_status` DISQUALIFIED must have a score of 0.",
    "A rule cannot be approved by the person who drafted it (separation of duties).",
    "One turnover row per business per month. Original system values are kept next to BM corrections.",
    "Accounts, turnover and product holdings belong to a business, never to the CUN, so businesses under one CUN stay separate.",
    "Returned debit-order counts cannot be negative. Three or more returns require a BM explanation, a relationship indicator and not a credit decision.",
    "Pipeline stages and outcomes are limited to the agreed values.",
]

DELIBERATE_GAPS = [
    "Missing values in business fields (entity type, sector, province, date established, employee count, recorded annual turnover) at roughly 3% to 8%.",
    "Missing director role and ID category at roughly 3% to 6%.",
    "Missing account type, account open date and holding start date at roughly 2% to 5%.",
    "About 1.5% of accounts are opened before their business was established.",
    "About 12% of businesses have no system turnover feed, and about 5% of other months are missing.",
    "Some clients with 3 or more returned debit orders have no BM explanation yet.",
]


def build():
    conn = sqlite3.connect(DB_PATH)
    out = []
    out.append("# Data Dictionary: Cubed Business Growth Intelligence Lab (PoC)\n")
    out.append("**All data is synthetic.** No real clients, CUNs, identity numbers, account numbers or confidential "
               "banking information are used. This dictionary is generated from the live database schema.\n")
    out.append("## Business rules enforced by the database\n")
    out += [f"- {r}" for r in BUSINESS_RULES]
    out.append("\n## Deliberate data-quality gaps\n")
    out += [f"- {g}" for g in DELIBERATE_GAPS]
    out.append("\n## Tables\n")
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        fks = {r[3]: f"{r[2]}.{r[4]}" for r in conn.execute(f"PRAGMA foreign_key_list({t})")}
        out.append(f"### `{t}`\n")
        out.append(f"{PURPOSE.get(t, '')}  \n*Rows in the synthetic PoC database: {count}*\n")
        out.append("| Column | Type | Required | Key | Description |")
        out.append("| --- | --- | --- | --- | --- |")
        for _cid, name, ctype, notnull, _default, pk in conn.execute(f"PRAGMA table_info({t})"):
            key = "PK" if pk else (f"FK to {fks[name]}" if name in fks else "")
            desc = DESCRIPTIONS.get(t, {}).get(name, "")
            out.append(f"| `{name}` | {ctype} | {'Yes' if notnull or pk else 'No'} | {key} | {desc} |")
        out.append("")
    conn.close()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(out))
    print(f"Data dictionary written: {OUTPUT}")


if __name__ == "__main__":
    build()
