-- COSA Startup Core baseline migration for services/company/commercial

-- GENERATED from a pg_dump --schema-only of the fully-migrated dev DB,
-- then filtered to the Founder Trial R1 retained allowlist. Review before use.
-- Task 10 of docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md

CREATE SCHEMA IF NOT EXISTS commercial;
CREATE SCHEMA IF NOT EXISTS sales;

CREATE TABLE IF NOT EXISTS commercial.marketing_campaigns (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    name character varying(255) NOT NULL,
    funnel_stage character varying(50) DEFAULT 'discover'::character varying NOT NULL,
    channels jsonb,
    budget double precision,
    status character varying(50) DEFAULT 'draft'::character varying NOT NULL,
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    project_id bigint
);

DO $$ BEGIN
  ALTER TABLE ONLY commercial.marketing_campaigns ADD CONSTRAINT marketing_campaigns_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY commercial.marketing_campaigns ADD CONSTRAINT marketing_campaigns_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_marketing_campaigns_project ON commercial.marketing_campaigns USING btree (workspace_id, project_id);

CREATE INDEX IF NOT EXISTS idx_marketing_campaigns_workspace ON commercial.marketing_campaigns USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS commercial.marketing_experiments (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    campaign_id bigint,
    name character varying(255) NOT NULL,
    hypothesis text NOT NULL,
    status character varying(50) DEFAULT 'draft'::character varying NOT NULL,
    baseline_metric character varying(100),
    baseline_value double precision,
    target_metric character varying(100),
    target_value double precision,
    actual_value double precision,
    conclusion text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    project_id bigint
);

DO $$ BEGIN
  ALTER TABLE ONLY commercial.marketing_experiments ADD CONSTRAINT marketing_experiments_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY commercial.marketing_experiments ADD CONSTRAINT marketing_experiments_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES commercial.marketing_campaigns(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY commercial.marketing_experiments ADD CONSTRAINT marketing_experiments_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_marketing_experiments_project ON commercial.marketing_experiments USING btree (workspace_id, project_id);

CREATE INDEX IF NOT EXISTS idx_marketing_experiments_workspace ON commercial.marketing_experiments USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS sales.contacts (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    account_id bigint,
    name text NOT NULL,
    title text,
    phone text,
    email text,
    source text,
    consent_status text,
    do_not_contact boolean DEFAULT false NOT NULL,
    owner_member_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    idempotency_key text
);

DO $$ BEGIN
  ALTER TABLE ONLY sales.contacts ADD CONSTRAINT contacts_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY sales.contacts ADD CONSTRAINT contacts_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_contacts_account_id ON sales.contacts USING btree (account_id);

CREATE INDEX IF NOT EXISTS idx_contacts_workspace_id ON sales.contacts USING btree (workspace_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_contacts_workspace_email ON sales.contacts USING btree (workspace_id, email) WHERE (email IS NOT NULL);


CREATE TABLE IF NOT EXISTS sales.contact_projects (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    contact_id bigint NOT NULL,
    project_id bigint NOT NULL,
    linked_by_member_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY sales.contact_projects ADD CONSTRAINT contact_projects_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY sales.contact_projects ADD CONSTRAINT contact_projects_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES sales.contacts(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY sales.contact_projects ADD CONSTRAINT contact_projects_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_contact_projects_project ON sales.contact_projects USING btree (workspace_id, project_id);

CREATE UNIQUE INDEX IF NOT EXISTS ux_contact_projects_pair ON sales.contact_projects USING btree (workspace_id, contact_id, project_id);


CREATE TABLE IF NOT EXISTS sales.sales_leads (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    key_result_id bigint,
    account_id bigint,
    contact_id bigint,
    name text NOT NULL,
    company text,
    stage text DEFAULT 'NEW'::text NOT NULL,
    value double precision,
    source text,
    source_campaign_id bigint,
    source_experiment_id bigint,
    utm_source text,
    utm_medium text,
    utm_campaign text,
    utm_content text,
    utm_term text,
    fit_score double precision,
    intent_score double precision,
    engagement_score double precision,
    qualification_status text,
    disqualification_reason text,
    next_action_at timestamp with time zone,
    next_action_type text,
    owner_member_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    idempotency_key text,
    project_id bigint
);

DO $$ BEGIN
  ALTER TABLE ONLY sales.sales_leads ADD CONSTRAINT sales_leads_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY sales.sales_leads ADD CONSTRAINT sales_leads_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY sales.sales_leads ADD CONSTRAINT sales_leads_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES sales.contacts(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY sales.sales_leads ADD CONSTRAINT sales_leads_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_sales_leads_account_id ON sales.sales_leads USING btree (account_id);

CREATE INDEX IF NOT EXISTS idx_sales_leads_contact_id ON sales.sales_leads USING btree (contact_id);

CREATE INDEX IF NOT EXISTS idx_sales_leads_key_result_id ON sales.sales_leads USING btree (key_result_id);

CREATE INDEX IF NOT EXISTS idx_sales_leads_project ON sales.sales_leads USING btree (workspace_id, project_id);

CREATE INDEX IF NOT EXISTS idx_sales_leads_workspace_id ON sales.sales_leads USING btree (workspace_id);



-- SP-A Task 5C2 — Khôi phục 22 bảng `commercial.*` / `sales.*` bị bỏ rơi trong
-- đợt squash baseline Founder Trial R1.
--
-- Bản squash gộp toàn bộ lịch sử migration commercial thành một file `001` nhưng
-- chỉ tạo 2 bảng `commercial.*` (marketing_campaigns, marketing_experiments) và
-- 3 bảng `sales.*` (contacts, contact_projects, sales_leads).
-- `services/company/shared/db/schema/commercial.ts` khai báo 21 `commercial.*` +
-- 6 `sales.*`. Drizzle schema là nguồn sự thật R1 (quyết định người dùng
-- 2026-09-10) — file này tạo lại 22 bảng còn thiếu:
--
--   commercial.campaign_assets, commercial.invoices,
--   commercial.marketing_attributions, commercial.marketing_context_evidence,
--   commercial.marketing_context_revisions, commercial.marketing_contexts,
--   commercial.marketing_customer_language,
--   commercial.marketing_customer_research_themes, commercial.marketing_decisions,
--   commercial.marketing_forms, commercial.marketing_icp_segments,
--   commercial.marketing_lead_intakes, commercial.marketing_learnings,
--   commercial.marketing_metric_definitions,
--   commercial.marketing_metric_observations, commercial.marketing_objectives,
--   commercial.marketing_product_marketing, commercial.marketing_proposals,
--   commercial.subscriptions, sales.accounts, sales.customers,
--   sales.sales_opportunities
--
-- Nguồn DDL: schema-only `pg_dump` của DB dev `workspace` (còn giữ nguyên schema
-- pre-squash đầy đủ) — được reset spec §7.3 cho phép dùng làm "comparison aid
-- for constraints and indexes". Cột / kiểu / DEFAULT / NOT NULL / CHECK sao chép
-- verbatim từ dump; đã đối chiếu 6 bảng (marketing_contexts,
-- marketing_context_revisions, subscriptions, invoices, sales.accounts,
-- sales.sales_opportunities) với `commercial.ts`.
--
-- Expand-only + idempotent: mọi `CREATE TABLE`/`CREATE INDEX` dùng
-- `IF NOT EXISTS`; mọi `ADD CONSTRAINT` bọc trong khối `DO ... EXCEPTION`. PK bọc
-- guard theo `pg_constraint` (thêm PK lần 2 raise `invalid_table_definition`,
-- KHÔNG phải `duplicate_object`). Không INSERT/UPDATE/DELETE, không
-- DROP/RENAME/TRUNCATE, không SET NOT NULL trên cột đã có.
--
-- Deviation so với dump:
--   * PK `id bigint` do app cấp (Snowflake). Dump có `CREATE SEQUENCE` +
--     `ALTER COLUMN id SET DEFAULT nextval(...)` cho một số bảng — BỎ toàn bộ
--     sequence + default, khớp `commercial.ts` (`.primaryKey()` trần) và đúng
--     tiền lệ `001` (001 cũng strip sequence của marketing_campaigns/experiments).
--   * `commercial.marketing_metric_observations.metric_id`: dump để NULLABLE,
--     `commercial.ts` khai `.notNull()` → theo Drizzle, tạo `NOT NULL` (bảng mới,
--     chưa có row nên expand-safe).
--   * `sales.accounts.idempotency_key` / `sales.sales_opportunities.idempotency_key`
--     + unique `(workspace_id, idempotency_key)`: `commercial.ts` KHÔNG khai cột
--     này nhưng dump có và `001` GIỮ cột tương ứng cho sales.contacts /
--     sales.sales_leads → giữ theo dump + tiền lệ `001` (cột nullable, nhiều NULL
--     hợp lệ trong UNIQUE nên không chặn insert).
--
-- Dropped FK: KHÔNG có. Mọi FK của 22 bảng đều trỏ tới bảng nằm trong bộ 22 này
-- hoặc trong `001` (commercial.marketing_campaigns, commercial.marketing_experiments,
-- sales.contacts, sales.sales_leads). Không FK nào trỏ `strategy.*` / `operating.*`.
--
-- Ngoài ra, 2 FK "ngược chiều" được thêm ở CUỐI phần ADD CONSTRAINT: bảng con
-- (`sales.contacts`, `sales.sales_leads`) do `001` tạo nhưng bảng cha
-- (`sales.accounts`) do `002` này tạo, nên FK phải nằm ở `002` (chạy sau khi
-- `002` tạo `sales.accounts`) — KHÔNG sửa `001`:
--   * sales.contacts.account_id    -> sales.accounts(id) ON DELETE CASCADE   (commercial.ts:26)
--   * sales.sales_leads.account_id -> sales.accounts(id) ON DELETE SET NULL  (commercial.ts:44)

-- =========================================================================
-- 1. CREATE TABLE (22 bảng còn thiếu)
-- =========================================================================

CREATE TABLE IF NOT EXISTS sales.accounts (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    name text NOT NULL,
    domain text,
    industry text,
    size_segment text,
    country text,
    source text,
    lifecycle_status text DEFAULT 'TARGET'::text NOT NULL,
    owner_member_id bigint,
    tags jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    idempotency_key text
);

CREATE TABLE IF NOT EXISTS sales.sales_opportunities (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    cycle_id bigint,
    account_id bigint NOT NULL,
    primary_contact_id bigint,
    owner_member_id bigint,
    source_lead_id bigint,
    product text,
    stage text DEFAULT 'DISCOVERY'::text NOT NULL,
    estimated_value double precision,
    currency text DEFAULT 'VND'::text NOT NULL,
    probability double precision,
    expected_close_date date,
    pain_points jsonb,
    needs jsonb,
    objections jsonb,
    competitors jsonb,
    next_action text,
    next_action_due_at timestamp with time zone,
    won_reason text,
    lost_reason text,
    lost_reason_detail text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    idempotency_key text
);

CREATE TABLE IF NOT EXISTS sales.customers (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    account_id bigint NOT NULL,
    acquired_from_opportunity_id bigint,
    lifecycle_status text DEFAULT 'ONBOARDING'::text NOT NULL,
    activation_status text,
    owner_member_id bigint,
    first_purchase_at timestamp with time zone,
    renewal_date date,
    health_status text DEFAULT 'HEALTHY'::text NOT NULL,
    last_success_interaction_at timestamp with time zone,
    next_success_action_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS commercial.marketing_contexts (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    revision integer DEFAULT 1 NOT NULL,
    status text DEFAULT 'draft'::text NOT NULL,
    updated_by_user_id bigint,
    reviewed_by_user_id bigint,
    reviewed_at timestamp with time zone,
    source_skill_id character varying(100),
    source_skill_version character varying(50),
    source_skill_hash character varying(64),
    offer_architecture jsonb,
    twelve_week_plan jsonb
);

CREATE TABLE IF NOT EXISTS commercial.marketing_context_revisions (
    id bigint NOT NULL,
    context_id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    revision integer NOT NULL,
    snapshot jsonb NOT NULL,
    created_by_user_id bigint,
    source_skill_id character varying(100),
    source_skill_version character varying(50),
    source_skill_hash character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS commercial.marketing_context_evidence (
    id bigint NOT NULL,
    context_id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    evidence_id character varying(100) NOT NULL,
    kind character varying(50) NOT NULL,
    source_url text,
    captured_at timestamp with time zone,
    captured_by character varying(100),
    confidence character varying(20) DEFAULT 'medium'::character varying NOT NULL,
    trust character varying(20) DEFAULT 'unreviewed'::character varying NOT NULL,
    sensitivity character varying(20) DEFAULT 'internal'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS commercial.marketing_customer_language (
    id bigint NOT NULL,
    context_id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    quote text NOT NULL,
    source_id character varying(100),
    captured_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS commercial.marketing_customer_research_themes (
    id bigint NOT NULL,
    context_id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    type character varying(50) NOT NULL,
    summary text NOT NULL,
    confidence character varying(20) DEFAULT 'medium'::character varying NOT NULL,
    evidence_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS commercial.marketing_icp_segments (
    id bigint NOT NULL,
    context_id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    segment text NOT NULL,
    confidence character varying(20) DEFAULT 'medium'::character varying NOT NULL,
    evidence_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS commercial.marketing_product_marketing (
    id bigint NOT NULL,
    context_id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    category character varying(255),
    positioning_statement text,
    alternatives jsonb DEFAULT '[]'::jsonb,
    differentiators jsonb DEFAULT '[]'::jsonb,
    brand_voice jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS commercial.campaign_assets (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    asset_type character varying(50) NOT NULL,
    title character varying(255) NOT NULL,
    content text NOT NULL,
    status character varying(50) DEFAULT 'draft'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS commercial.marketing_forms (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    title character varying(255) NOT NULL,
    slug character varying(255) NOT NULL,
    fields_schema jsonb DEFAULT '[]'::jsonb NOT NULL,
    is_published boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS commercial.marketing_lead_intakes (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    form_id bigint,
    contact_data jsonb DEFAULT '{}'::jsonb NOT NULL,
    source character varying(100),
    status character varying(50) DEFAULT 'new'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS commercial.marketing_objectives (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    target_metric character varying(100),
    target_value double precision,
    current_value double precision,
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS commercial.marketing_learnings (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    experiment_id bigint,
    title character varying(255) NOT NULL,
    insight text NOT NULL,
    impact character varying(50) DEFAULT 'medium'::character varying NOT NULL,
    action_items jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS commercial.marketing_metric_definitions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    name character varying(100) NOT NULL,
    unit character varying(50) DEFAULT 'count'::character varying NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS commercial.marketing_metric_observations (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    metric_id bigint NOT NULL,
    provider_key text NOT NULL,
    source_record_id text NOT NULL,
    payload_hash text NOT NULL,
    observed_at timestamp with time zone NOT NULL,
    ingested_at timestamp with time zone DEFAULT now() NOT NULL,
    value double precision NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL
);

CREATE TABLE IF NOT EXISTS commercial.marketing_attributions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    campaign_id bigint,
    channel character varying(100) NOT NULL,
    touchpoint_type character varying(50) NOT NULL,
    conversions double precision DEFAULT 0 NOT NULL,
    revenue double precision DEFAULT 0 NOT NULL,
    observed_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS commercial.marketing_decisions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    campaign_id bigint,
    title character varying(255) NOT NULL,
    rationale text NOT NULL,
    decision_type character varying(50) NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    created_by character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS commercial.marketing_proposals (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    title character varying(255) NOT NULL,
    proposal_type character varying(50) NOT NULL,
    origin character varying(50) NOT NULL,
    status character varying(50) NOT NULL,
    source_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    body jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_by character varying(255) NOT NULL,
    reviewed_by character varying(255),
    reviewed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT marketing_proposals_origin_check CHECK (((origin)::text = ANY ((ARRAY['USER'::character varying, 'MODEL_DRAFT'::character varying])::text[]))),
    CONSTRAINT marketing_proposals_status_check CHECK (((status)::text = ANY ((ARRAY['DRAFT'::character varying, 'IN_REVIEW'::character varying, 'APPROVED'::character varying, 'REJECTED'::character varying])::text[])))
);

CREATE TABLE IF NOT EXISTS commercial.invoices (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    customer_id bigint,
    invoice_number character varying(100) NOT NULL,
    amount double precision NOT NULL,
    currency character varying(10) DEFAULT 'VND'::character varying NOT NULL,
    status character varying(50) DEFAULT 'draft'::character varying NOT NULL,
    due_date timestamp with time zone,
    paid_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS commercial.subscriptions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    customer_id bigint,
    plan_name character varying(100) NOT NULL,
    billing_cycle character varying(50) DEFAULT 'monthly'::character varying NOT NULL,
    price double precision NOT NULL,
    currency character varying(10) DEFAULT 'VND'::character varying NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    current_period_start timestamp with time zone,
    current_period_end timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

-- =========================================================================
-- 2. CREATE INDEX (chỉ index của 22 bảng trên)
-- =========================================================================

CREATE INDEX IF NOT EXISTS idx_campaign_assets_campaign ON commercial.campaign_assets USING btree (campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_assets_workspace ON commercial.campaign_assets USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_invoices_workspace ON commercial.invoices USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_attributions_workspace ON commercial.marketing_attributions USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_context_evidence_context ON commercial.marketing_context_evidence USING btree (context_id);
CREATE INDEX IF NOT EXISTS idx_marketing_context_evidence_workspace ON commercial.marketing_context_evidence USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_context_revisions_context ON commercial.marketing_context_revisions USING btree (context_id);
CREATE INDEX IF NOT EXISTS idx_marketing_context_revisions_lookup ON commercial.marketing_context_revisions USING btree (context_id, revision);
CREATE INDEX IF NOT EXISTS idx_marketing_context_revisions_workspace ON commercial.marketing_context_revisions USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_contexts_workspace ON commercial.marketing_contexts USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_customer_language_context ON commercial.marketing_customer_language USING btree (context_id);
CREATE INDEX IF NOT EXISTS idx_marketing_customer_language_workspace ON commercial.marketing_customer_language USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_customer_research_themes_context ON commercial.marketing_customer_research_themes USING btree (context_id);
CREATE INDEX IF NOT EXISTS idx_marketing_customer_research_themes_workspace ON commercial.marketing_customer_research_themes USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_decisions_workspace ON commercial.marketing_decisions USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_forms_workspace ON commercial.marketing_forms USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_icp_segments_context ON commercial.marketing_icp_segments USING btree (context_id);
CREATE INDEX IF NOT EXISTS idx_marketing_icp_segments_workspace ON commercial.marketing_icp_segments USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_lead_intakes_workspace ON commercial.marketing_lead_intakes USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_learnings_workspace ON commercial.marketing_learnings USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_metric_defs_workspace ON commercial.marketing_metric_definitions USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_metric_obs_workspace ON commercial.marketing_metric_observations USING btree (workspace_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_marketing_objectives_workspace ON commercial.marketing_objectives USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_product_marketing_context ON commercial.marketing_product_marketing USING btree (context_id);
CREATE INDEX IF NOT EXISTS idx_marketing_product_marketing_workspace ON commercial.marketing_product_marketing USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_marketing_proposals_workspace ON commercial.marketing_proposals USING btree (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_workspace ON commercial.subscriptions USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_accounts_workspace_id ON sales.accounts USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_customers_workspace_id ON sales.customers USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_account_id ON sales.sales_opportunities USING btree (account_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_workspace_id ON sales.sales_opportunities USING btree (workspace_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_accounts_workspace_domain ON sales.accounts USING btree (workspace_id, domain) WHERE (domain IS NOT NULL);

-- =========================================================================
-- 3. ADD CONSTRAINT — bọc DO để idempotent khi re-apply thô
-- =========================================================================

-- ---- PRIMARY KEY (guard theo pg_constraint) ----
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'sales.accounts'::regclass AND contype = 'p') THEN ALTER TABLE sales.accounts ADD CONSTRAINT accounts_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'sales.sales_opportunities'::regclass AND contype = 'p') THEN ALTER TABLE sales.sales_opportunities ADD CONSTRAINT sales_opportunities_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'sales.customers'::regclass AND contype = 'p') THEN ALTER TABLE sales.customers ADD CONSTRAINT customers_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_contexts'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_contexts ADD CONSTRAINT marketing_contexts_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_context_revisions'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_context_revisions ADD CONSTRAINT marketing_context_revisions_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_context_evidence'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_context_evidence ADD CONSTRAINT marketing_context_evidence_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_customer_language'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_customer_language ADD CONSTRAINT marketing_customer_language_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_customer_research_themes'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_customer_research_themes ADD CONSTRAINT marketing_customer_research_themes_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_icp_segments'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_icp_segments ADD CONSTRAINT marketing_icp_segments_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_product_marketing'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_product_marketing ADD CONSTRAINT marketing_product_marketing_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.campaign_assets'::regclass AND contype = 'p') THEN ALTER TABLE commercial.campaign_assets ADD CONSTRAINT campaign_assets_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_forms'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_forms ADD CONSTRAINT marketing_forms_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_lead_intakes'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_lead_intakes ADD CONSTRAINT marketing_lead_intakes_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_objectives'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_objectives ADD CONSTRAINT marketing_objectives_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_learnings'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_learnings ADD CONSTRAINT marketing_learnings_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_metric_definitions'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_metric_definitions ADD CONSTRAINT marketing_metric_definitions_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_metric_observations'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_metric_observations ADD CONSTRAINT marketing_metric_observations_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_attributions'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_attributions ADD CONSTRAINT marketing_attributions_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_decisions'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_decisions ADD CONSTRAINT marketing_decisions_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.marketing_proposals'::regclass AND contype = 'p') THEN ALTER TABLE commercial.marketing_proposals ADD CONSTRAINT marketing_proposals_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.invoices'::regclass AND contype = 'p') THEN ALTER TABLE commercial.invoices ADD CONSTRAINT invoices_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'commercial.subscriptions'::regclass AND contype = 'p') THEN ALTER TABLE commercial.subscriptions ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;

-- ---- UNIQUE ----
DO $$ BEGIN ALTER TABLE commercial.marketing_metric_definitions ADD CONSTRAINT marketing_metric_definitions_workspace_id_name_key UNIQUE (workspace_id, name); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_metric_observations ADD CONSTRAINT marketing_metric_observations_workspace_id_provider_key_sou_key UNIQUE (workspace_id, provider_key, source_record_id, payload_hash); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.invoices ADD CONSTRAINT uix_invoices_workspace_number UNIQUE (workspace_id, invoice_number); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_context_evidence ADD CONSTRAINT uix_marketing_context_evidence_id UNIQUE (context_id, evidence_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_contexts ADD CONSTRAINT uix_marketing_contexts_workspace UNIQUE (workspace_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_forms ADD CONSTRAINT uix_marketing_forms_slug UNIQUE (workspace_id, slug); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_product_marketing ADD CONSTRAINT uix_marketing_product_marketing_context UNIQUE (context_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE sales.accounts ADD CONSTRAINT accounts_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE sales.customers ADD CONSTRAINT customers_workspace_id_account_id_key UNIQUE (workspace_id, account_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE sales.sales_opportunities ADD CONSTRAINT sales_opportunities_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;

-- ---- FOREIGN KEY (target nằm trong bộ 22 này hoặc trong `001`) ----
DO $$ BEGIN ALTER TABLE commercial.campaign_assets ADD CONSTRAINT campaign_assets_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES commercial.marketing_campaigns(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.invoices ADD CONSTRAINT invoices_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES sales.customers(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_attributions ADD CONSTRAINT marketing_attributions_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES commercial.marketing_campaigns(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_context_evidence ADD CONSTRAINT marketing_context_evidence_context_id_fkey FOREIGN KEY (context_id) REFERENCES commercial.marketing_contexts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_context_revisions ADD CONSTRAINT marketing_context_revisions_context_id_fkey FOREIGN KEY (context_id) REFERENCES commercial.marketing_contexts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_customer_language ADD CONSTRAINT marketing_customer_language_context_id_fkey FOREIGN KEY (context_id) REFERENCES commercial.marketing_contexts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_customer_research_themes ADD CONSTRAINT marketing_customer_research_themes_context_id_fkey FOREIGN KEY (context_id) REFERENCES commercial.marketing_contexts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_decisions ADD CONSTRAINT marketing_decisions_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES commercial.marketing_campaigns(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_icp_segments ADD CONSTRAINT marketing_icp_segments_context_id_fkey FOREIGN KEY (context_id) REFERENCES commercial.marketing_contexts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_lead_intakes ADD CONSTRAINT marketing_lead_intakes_form_id_fkey FOREIGN KEY (form_id) REFERENCES commercial.marketing_forms(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_learnings ADD CONSTRAINT marketing_learnings_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES commercial.marketing_experiments(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_metric_observations ADD CONSTRAINT marketing_metric_observations_metric_id_fkey FOREIGN KEY (metric_id) REFERENCES commercial.marketing_metric_definitions(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.marketing_product_marketing ADD CONSTRAINT marketing_product_marketing_context_id_fkey FOREIGN KEY (context_id) REFERENCES commercial.marketing_contexts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE commercial.subscriptions ADD CONSTRAINT subscriptions_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES sales.customers(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE sales.customers ADD CONSTRAINT customers_account_id_fkey FOREIGN KEY (account_id) REFERENCES sales.accounts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE sales.customers ADD CONSTRAINT customers_acquired_from_opportunity_id_fkey FOREIGN KEY (acquired_from_opportunity_id) REFERENCES sales.sales_opportunities(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE sales.sales_opportunities ADD CONSTRAINT sales_opportunities_account_id_fkey FOREIGN KEY (account_id) REFERENCES sales.accounts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE sales.sales_opportunities ADD CONSTRAINT sales_opportunities_primary_contact_id_fkey FOREIGN KEY (primary_contact_id) REFERENCES sales.contacts(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE sales.sales_opportunities ADD CONSTRAINT sales_opportunities_source_lead_id_fkey FOREIGN KEY (source_lead_id) REFERENCES sales.sales_leads(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;

-- ---- FOREIGN KEY ngược chiều: bảng con ở `001`, bảng cha `sales.accounts` ở `002` ----
DO $$ BEGIN ALTER TABLE sales.contacts ADD CONSTRAINT contacts_account_id_fkey FOREIGN KEY (account_id) REFERENCES sales.accounts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE sales.sales_leads ADD CONSTRAINT sales_leads_account_id_fkey FOREIGN KEY (account_id) REFERENCES sales.accounts(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
