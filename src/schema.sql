-- Cubed Business Growth Intelligence Lab: PoC schema (SYNTHETIC DATA ONLY)
PRAGMA foreign_keys = ON;

CREATE TABLE users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT NOT NULL UNIQUE,
    full_name   TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('Business Manager','Area Manager','MIS Analyst',
                                              'Product Owner','Compliance and Audit','System Admin')),
    area        TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1))
);

CREATE TABLE client_master (
    client_id           INTEGER PRIMARY KEY,
    cun                 TEXT NOT NULL UNIQUE,          -- synthetic format, e.g. SYN-000001
    client_name         TEXT NOT NULL,
    segment             TEXT,
    relationship_start  TEXT,
    assigned_bm_id      INTEGER REFERENCES users(user_id),
    status              TEXT NOT NULL DEFAULT 'Active',
    is_synthetic        INTEGER NOT NULL DEFAULT 1 CHECK (is_synthetic = 1)
);

CREATE TABLE businesses (
    business_id                INTEGER PRIMARY KEY,
    client_id                  INTEGER NOT NULL REFERENCES client_master(client_id),
    business_name              TEXT NOT NULL,
    entity_type                TEXT,
    industry_sector            TEXT,
    province                   TEXT,
    date_established           TEXT,
    employee_count             INTEGER CHECK (employee_count IS NULL OR employee_count >= 0),
    recorded_annual_turnover   REAL CHECK (recorded_annual_turnover IS NULL OR recorded_annual_turnover >= 0),
    status                     TEXT NOT NULL DEFAULT 'Active'
);

CREATE TABLE directors (
    director_id     INTEGER PRIMARY KEY,
    business_id     INTEGER NOT NULL REFERENCES businesses(business_id),
    full_name       TEXT NOT NULL,
    role            TEXT,                               -- Director, Proprietor, etc.
    id_category     TEXT                                -- category only, never an ID number
);

CREATE TABLE accounts (
    account_id      INTEGER PRIMARY KEY,
    business_id     INTEGER NOT NULL REFERENCES businesses(business_id),
    account_ref     TEXT NOT NULL UNIQUE,               -- synthetic reference
    account_type    TEXT,
    open_date       TEXT,
    status          TEXT NOT NULL DEFAULT 'Open'
);

CREATE TABLE product_holdings (
    holding_id      INTEGER PRIMARY KEY,
    business_id     INTEGER NOT NULL REFERENCES businesses(business_id),
    account_id      INTEGER REFERENCES accounts(account_id),
    product_code    TEXT NOT NULL,
    product_name    TEXT NOT NULL,
    start_date      TEXT,
    status          TEXT NOT NULL DEFAULT 'Active'
);

CREATE TABLE monthly_turnover (
    turnover_id         INTEGER PRIMARY KEY,
    business_id         INTEGER NOT NULL REFERENCES businesses(business_id),
    account_id          INTEGER REFERENCES accounts(account_id),
    month               TEXT NOT NULL,                  -- YYYY-MM
    system_value        REAL CHECK (system_value IS NULL OR system_value >= 0),
    bm_value            REAL CHECK (bm_value IS NULL OR bm_value >= 0),
    value_source        TEXT NOT NULL CHECK (value_source IN ('SYSTEM','BM','MISSING')),
    captured_by         INTEGER REFERENCES users(user_id),
    captured_at         TEXT,
    UNIQUE (business_id, month)
);

CREATE TABLE account_conduct (
    conduct_id              INTEGER PRIMARY KEY,
    account_id              INTEGER NOT NULL REFERENCES accounts(account_id),
    period_end              TEXT NOT NULL,
    returned_debit_orders   INTEGER NOT NULL CHECK (returned_debit_orders >= 0),
    return_reasons          TEXT,
    bm_explanation          TEXT,
    recorded_by             INTEGER REFERENCES users(user_id),
    recorded_at             TEXT
);

CREATE TABLE product_rules (
    rule_id         INTEGER PRIMARY KEY,
    product_code    TEXT NOT NULL,
    rule_name       TEXT NOT NULL,
    rule_type       TEXT NOT NULL CHECK (rule_type IN ('ELIGIBILITY','SCORING')),
    parameters      TEXT,                               -- rule definition (JSON text)
    points          INTEGER,
    version         INTEGER NOT NULL DEFAULT 1,
    approval_status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (approval_status IN ('DRAFT','APPROVED','RETIRED')),
    drafted_by      INTEGER REFERENCES users(user_id),
    approved_by     INTEGER REFERENCES users(user_id),
    CHECK (approved_by IS NULL OR approved_by <> drafted_by)   -- separation of duties
);

CREATE TABLE product_recommendations (
    recommendation_id   INTEGER PRIMARY KEY,
    business_id         INTEGER NOT NULL REFERENCES businesses(business_id),
    product_code        TEXT NOT NULL,
    take_up_score       INTEGER NOT NULL CHECK (take_up_score BETWEEN 0 AND 5),
    eligibility_status  TEXT NOT NULL CHECK (eligibility_status IN ('ELIGIBLE','ELIGIBLE_WITH_CONDITIONS','DISQUALIFIED')),
    rank_position       INTEGER,
    reason_codes        TEXT,
    rule_version        INTEGER,
    generated_at        TEXT,
    CHECK (eligibility_status <> 'DISQUALIFIED' OR take_up_score = 0)
);

CREATE TABLE discussion_assists (
    assist_id           INTEGER PRIMARY KEY,
    product_code        TEXT NOT NULL,
    recommendation_id   INTEGER REFERENCES product_recommendations(recommendation_id),
    approved_script     TEXT NOT NULL,
    ai_enhanced_guide   TEXT,
    script_version      INTEGER NOT NULL DEFAULT 1,
    approval_status     TEXT NOT NULL DEFAULT 'DRAFT' CHECK (approval_status IN ('DRAFT','APPROVED','RETIRED')),
    approved_by         INTEGER REFERENCES users(user_id),
    created_at          TEXT
);

CREATE TABLE client_engagements (
    engagement_id       INTEGER PRIMARY KEY,
    business_id         INTEGER NOT NULL REFERENCES businesses(business_id),
    user_id             INTEGER NOT NULL REFERENCES users(user_id),
    recommendation_id   INTEGER REFERENCES product_recommendations(recommendation_id),
    engagement_date     TEXT NOT NULL,
    notes               TEXT,
    client_response     TEXT,
    agreed_action       TEXT
);

CREATE TABLE crm_pipeline (
    opportunity_id      INTEGER PRIMARY KEY,
    business_id         INTEGER NOT NULL REFERENCES businesses(business_id),
    engagement_id       INTEGER REFERENCES client_engagements(engagement_id),
    product_code        TEXT NOT NULL,
    stage               TEXT NOT NULL CHECK (stage IN ('Identified','Contacted','Discussed','Interested','Referred','Handed over')),
    owner_user_id       INTEGER REFERENCES users(user_id),
    next_followup_date  TEXT,
    handover_to         INTEGER REFERENCES users(user_id),
    outcome             TEXT CHECK (outcome IS NULL OR outcome IN ('Won','Lost','Deferred')),
    created_at          TEXT,
    updated_at          TEXT
);

CREATE TABLE audit_logs (
    log_id          INTEGER PRIMARY KEY,
    logged_at       TEXT NOT NULL,
    user_id         INTEGER REFERENCES users(user_id),
    table_name      TEXT NOT NULL,
    record_id       INTEGER,
    action          TEXT NOT NULL CHECK (action IN ('INSERT','UPDATE','DELETE','VIEW')),
    old_value       TEXT,
    new_value       TEXT,
    rule_version    INTEGER
);

CREATE INDEX idx_businesses_client   ON businesses(client_id);
CREATE INDEX idx_directors_business  ON directors(business_id);
CREATE INDEX idx_accounts_business   ON accounts(business_id);
CREATE INDEX idx_holdings_business   ON product_holdings(business_id);
CREATE INDEX idx_turnover_business   ON monthly_turnover(business_id);
CREATE INDEX idx_conduct_account     ON account_conduct(account_id);
CREATE INDEX idx_reco_business       ON product_recommendations(business_id);
CREATE INDEX idx_engage_business     ON client_engagements(business_id);
CREATE INDEX idx_pipeline_business   ON crm_pipeline(business_id);
CREATE INDEX idx_audit_table         ON audit_logs(table_name, record_id);

