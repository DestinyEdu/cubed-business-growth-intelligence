# Data Dictionary: Cubed Business Growth Intelligence Lab (PoC)

**All data is synthetic.** No real clients, CUNs, identity numbers, account numbers or confidential banking information are used. This dictionary is generated from the live database schema.

## Business rules enforced by the database

- Every client is synthetic: `is_synthetic` must be 1.
- `take_up_score` is between 0 and 5. A product with `eligibility_status` DISQUALIFIED must have a score of 0.
- A rule cannot be approved by the person who drafted it (separation of duties).
- One turnover row per business per month. Original system values are kept next to BM corrections.
- Accounts, turnover and product holdings belong to a business, never to the CUN, so businesses under one CUN stay separate.
- Returned debit-order counts cannot be negative. Three or more returns require a BM explanation, a relationship indicator and not a credit decision.
- Pipeline stages and outcomes are limited to the agreed values.

## Deliberate data-quality gaps

- Missing values in business fields (entity type, sector, province, date established, employee count, recorded annual turnover) at roughly 3% to 8%.
- Missing director role and ID category at roughly 3% to 6%.
- Missing account type, account open date and holding start date at roughly 2% to 5%.
- About 1.5% of accounts are opened before their business was established.
- About 12% of businesses have no system turnover feed, and about 5% of other months are missing.
- Some clients with 3 or more returned debit orders have no BM explanation yet.

## Tables

### `account_conduct`

Returned debit orders for an account, with return reasons and the BM explanation.  
*Rows in the synthetic PoC database: 641*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `conduct_id` | INTEGER | Yes | PK | Internal identifier. |
| `account_id` | INTEGER | Yes | FK to accounts.account_id | The account the conduct relates to. |
| `period_end` | TEXT | Yes |  | End date of the six-month conduct window. |
| `returned_debit_orders` | INTEGER | Yes |  | Number of returned debit orders in the six months. |
| `return_reasons` | TEXT | No |  | Semicolon-separated return reasons. Empty when there are no returns. |
| `bm_explanation` | TEXT | No |  | Client explanation recorded by the BM. Required for 3 or more returns. |
| `recorded_by` | INTEGER | No | FK to users.user_id | Business Manager who recorded the explanation. |
| `recorded_at` | TEXT | No |  | Date the explanation was recorded. |

### `accounts`

Client accounts and account-level information. Attached to a business, never to the CUN.  
*Rows in the synthetic PoC database: 932*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `account_id` | INTEGER | Yes | PK | Internal identifier. |
| `business_id` | INTEGER | Yes | FK to businesses.business_id | The business that owns the account. |
| `account_ref` | TEXT | Yes |  | Synthetic account reference, format SYN-ACC-######## (unique). |
| `account_type` | TEXT | No |  | Cheque, savings or notice deposit. May be missing. |
| `open_date` | TEXT | No |  | Date the account was opened (ISO date). May be missing. |
| `status` | TEXT | Yes |  | Open, Dormant or Closed. |

### `audit_logs`

Changes, timestamps, user actions and rule versions.  
*Rows in the synthetic PoC database: 0*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `log_id` | INTEGER | Yes | PK | Internal identifier. |
| `logged_at` | TEXT | Yes |  | Timestamp of the action. |
| `user_id` | INTEGER | No | FK to users.user_id | User who performed the action. |
| `table_name` | TEXT | Yes |  | Table affected. |
| `record_id` | INTEGER | No |  | Record affected. |
| `action` | TEXT | Yes |  | INSERT, UPDATE, DELETE or VIEW. |
| `old_value` | TEXT | No |  | Value before the change. |
| `new_value` | TEXT | No |  | Value after the change. |
| `rule_version` | INTEGER | No |  | Rule version in force at the time. |

### `businesses`

Business profiles and entity details. One CUN can link to several businesses.  
*Rows in the synthetic PoC database: 641*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `business_id` | INTEGER | Yes | PK | Internal identifier. |
| `client_id` | INTEGER | Yes | FK to client_master.client_id | The client (CUN) this business belongs to. |
| `business_name` | TEXT | Yes |  | Fictional business name. |
| `entity_type` | TEXT | No |  | Private company, close corporation, sole proprietor, partnership or trust. May be missing. |
| `industry_sector` | TEXT | No |  | Industry sector. May be missing. |
| `province` | TEXT | No |  | South African province. May be missing. |
| `date_established` | TEXT | No |  | Date the business was established (ISO date). May be missing. |
| `employee_count` | INTEGER | No |  | Number of employees. May be missing. |
| `recorded_annual_turnover` | REAL | No |  | Recorded annual turnover in rand. Not verified. May be missing. |
| `status` | TEXT | Yes |  | Business status. |

### `client_engagements`

BM notes, client responses and agreed actions.  
*Rows in the synthetic PoC database: 0*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `engagement_id` | INTEGER | Yes | PK | Internal identifier. |
| `business_id` | INTEGER | Yes | FK to businesses.business_id | The business discussed. |
| `user_id` | INTEGER | Yes | FK to users.user_id | Business Manager who recorded the engagement. |
| `recommendation_id` | INTEGER | No | FK to product_recommendations.recommendation_id | Recommendation discussed, if any. |
| `engagement_date` | TEXT | Yes |  | Date of the conversation. |
| `notes` | TEXT | No |  | BM notes. |
| `client_response` | TEXT | No |  | The client's response. |
| `agreed_action` | TEXT | No |  | Action agreed with the client. |

### `client_master`

CUN and core client information.  
*Rows in the synthetic PoC database: 500*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `client_id` | INTEGER | Yes | PK | Internal identifier. |
| `cun` | TEXT | Yes |  | Synthetic Customer Unique Number, format SYN-000000 (unique). |
| `client_name` | TEXT | Yes |  | Name of the client's primary business. |
| `segment` | TEXT | No |  | Illustrative PoC segment band (Micro, Small, Medium, Large SME) derived from turnover. May be missing. |
| `relationship_start` | TEXT | No |  | Date the client relationship began (ISO date). |
| `assigned_bm_id` | INTEGER | No | FK to users.user_id | Business Manager responsible for the client. |
| `status` | TEXT | Yes |  | Active or Dormant. |
| `is_synthetic` | INTEGER | Yes |  | Always 1. The database rejects any other value. |

### `crm_pipeline`

Opportunities, stages, handovers and outcomes.  
*Rows in the synthetic PoC database: 0*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `opportunity_id` | INTEGER | Yes | PK | Internal identifier. |
| `business_id` | INTEGER | Yes | FK to businesses.business_id | The business the opportunity is for. |
| `engagement_id` | INTEGER | No | FK to client_engagements.engagement_id | Engagement the opportunity came from. |
| `product_code` | TEXT | Yes |  | Product in the opportunity. |
| `stage` | TEXT | Yes |  | Identified, Contacted, Discussed, Interested, Referred or Handed over. |
| `owner_user_id` | INTEGER | No | FK to users.user_id | Current owner of the opportunity. |
| `next_followup_date` | TEXT | No |  | Date of the next follow-up. |
| `handover_to` | INTEGER | No | FK to users.user_id | User the opportunity was handed over to. |
| `outcome` | TEXT | No |  | Won, Lost or Deferred. Empty while the opportunity is open. |
| `created_at` | TEXT | No |  | When the opportunity was created. |
| `updated_at` | TEXT | No |  | When the opportunity was last updated. |

### `directors`

Directors, proprietors and identification categories.  
*Rows in the synthetic PoC database: 1111*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `director_id` | INTEGER | Yes | PK | Internal identifier. |
| `business_id` | INTEGER | Yes | FK to businesses.business_id | The business the director or proprietor belongs to. |
| `full_name` | TEXT | Yes |  | Fictional name. |
| `role` | TEXT | No |  | Director, Member, Trustee, Partner or Proprietor. May be missing. |
| `id_category` | TEXT | No |  | Identification category only (never an ID number). May be missing. |

### `discussion_assists`

Approved product scripts and the AI-enhanced discussion guides built from them.  
*Rows in the synthetic PoC database: 0*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `assist_id` | INTEGER | Yes | PK | Internal identifier. |
| `product_code` | TEXT | Yes |  | Product the script belongs to. |
| `recommendation_id` | INTEGER | No | FK to product_recommendations.recommendation_id | Recommendation the guide was built for. |
| `approved_script` | TEXT | Yes |  | Approved product script text. |
| `ai_enhanced_guide` | TEXT | No |  | Client-specific guide built from the approved script. |
| `script_version` | INTEGER | Yes |  | Script version. |
| `approval_status` | TEXT | Yes |  | DRAFT, APPROVED or RETIRED. |
| `approved_by` | INTEGER | No | FK to users.user_id | Approver of the script. |
| `created_at` | TEXT | No |  | When the record was created. |

### `monthly_turnover`

Six monthly turnover records, with the system value and any BM correction held side by side.  
*Rows in the synthetic PoC database: 3846*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `turnover_id` | INTEGER | Yes | PK | Internal identifier. |
| `business_id` | INTEGER | Yes | FK to businesses.business_id | The business the turnover belongs to. |
| `account_id` | INTEGER | No | FK to accounts.account_id | Cheque account the turnover relates to. |
| `month` | TEXT | Yes |  | Month in YYYY-MM format. One row per business per month. |
| `system_value` | REAL | No |  | System pre-populated turnover in rand. Empty if none was available. |
| `bm_value` | REAL | No |  | Value captured or corrected by the Business Manager. The system value is retained alongside it. |
| `value_source` | TEXT | Yes |  | SYSTEM, BM or MISSING. |
| `captured_by` | INTEGER | No | FK to users.user_id | Business Manager who captured or corrected the value. |
| `captured_at` | TEXT | No |  | Date of the BM capture or correction. |

### `product_holdings`

Existing products and services held by a business.  
*Rows in the synthetic PoC database: 1584*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `holding_id` | INTEGER | Yes | PK | Internal identifier. |
| `business_id` | INTEGER | Yes | FK to businesses.business_id | The business holding the product. |
| `account_id` | INTEGER | No | FK to accounts.account_id | Linked account where the product is account-based. May be empty. |
| `product_code` | TEXT | Yes |  | Code from the illustrative product catalogue. |
| `product_name` | TEXT | Yes |  | Name from the illustrative product catalogue. |
| `start_date` | TEXT | No |  | Date the product started (ISO date). May be missing. |
| `status` | TEXT | Yes |  | Active or Closed. |

### `product_recommendations`

Eligibility, take-up score, ranking and reason codes per product and business.  
*Rows in the synthetic PoC database: 0*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `recommendation_id` | INTEGER | Yes | PK | Internal identifier. |
| `business_id` | INTEGER | Yes | FK to businesses.business_id | The business the recommendation is for. |
| `product_code` | TEXT | Yes |  | Product being evaluated. |
| `take_up_score` | INTEGER | Yes |  | Estimated commercial take-up potential, 0 to 5. Not creditworthiness. |
| `eligibility_status` | TEXT | Yes |  | ELIGIBLE, ELIGIBLE_WITH_CONDITIONS or DISQUALIFIED. A disqualified product must score 0. |
| `rank_position` | INTEGER | No |  | Rank among the business's products by take-up likelihood. |
| `reason_codes` | TEXT | No |  | Plain-language reasons behind the score and eligibility. |
| `rule_version` | INTEGER | No |  | Rule version used to produce the score. |
| `generated_at` | TEXT | No |  | When the recommendation was generated. |

### `product_rules`

Configurable, versioned product eligibility and scoring rules.  
*Rows in the synthetic PoC database: 0*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `rule_id` | INTEGER | Yes | PK | Internal identifier. |
| `product_code` | TEXT | Yes |  | Product the rule applies to. |
| `rule_name` | TEXT | Yes |  | Short rule name. |
| `rule_type` | TEXT | Yes |  | ELIGIBILITY or SCORING. |
| `parameters` | TEXT | No |  | Rule definition (JSON text). |
| `points` | INTEGER | No |  | Points awarded when a scoring rule applies. |
| `version` | INTEGER | Yes |  | Rule version, recorded for audit. |
| `approval_status` | TEXT | Yes |  | DRAFT, APPROVED or RETIRED. |
| `drafted_by` | INTEGER | No | FK to users.user_id | Product Owner who drafted the rule. |
| `approved_by` | INTEGER | No | FK to users.user_id | Compliance and Audit approver. Must differ from drafted_by. |

### `users`

Simulated Business Manager and management users.  
*Rows in the synthetic PoC database: 19*

| Column | Type | Required | Key | Description |
| --- | --- | --- | --- | --- |
| `user_id` | INTEGER | Yes | PK | Unique user identifier. |
| `username` | TEXT | Yes |  | Simulated login name (unique). |
| `full_name` | TEXT | Yes |  | Fictional name. |
| `role` | TEXT | Yes |  | RBAC role: Business Manager, Area Manager, MIS Analyst, Product Owner, Compliance and Audit or System Admin. |
| `area` | TEXT | No |  | Area for Business Managers and Area Managers; empty for central roles. |
| `is_active` | INTEGER | Yes |  | 1 = active, 0 = inactive. |
