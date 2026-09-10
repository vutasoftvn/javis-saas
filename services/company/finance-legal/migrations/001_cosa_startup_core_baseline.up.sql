-- COSA Startup Core baseline migration for services/company/finance-legal

-- GENERATED from a pg_dump --schema-only of the fully-migrated dev DB,
-- then filtered to the Founder Trial R1 retained allowlist. Review before use.
-- Task 10 of docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md

CREATE SCHEMA IF NOT EXISTS finance;

CREATE TABLE IF NOT EXISTS finance.bank_connections (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    provider text NOT NULL,
    consent_state text DEFAULT 'PENDING'::text NOT NULL,
    secret_ref text,
    scopes jsonb DEFAULT '[]'::jsonb NOT NULL,
    account_links jsonb DEFAULT '[]'::jsonb NOT NULL,
    grant_expires_at timestamp with time zone,
    last_synced_at timestamp with time zone,
    sync_status text DEFAULT 'IDLE'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    legal_entity_id bigint,
    provider_environment text DEFAULT 'sandbox'::text NOT NULL,
    provider_grant_id text,
    external_account_id text,
    institution_id text,
    account_fingerprint text,
    granted_scopes jsonb DEFAULT '[]'::jsonb NOT NULL,
    grant_expires_at_v2 timestamp with time zone,
    provider_contract_version text,
    reauth_required boolean DEFAULT false NOT NULL,
    sync_cursor text,
    sync_error text,
    sync_error_count integer DEFAULT 0 NOT NULL,
    sync_locked_until timestamp with time zone,
    sync_coverage_start timestamp with time zone,
    CONSTRAINT bank_connections_consent_state_check CHECK ((consent_state = ANY (ARRAY['PENDING'::text, 'GRANTED'::text, 'REVOKED'::text, 'EXPIRED'::text]))),
    CONSTRAINT bank_connections_provider_check CHECK ((provider = ANY (ARRAY['cas'::text, 'manual'::text]))),
    CONSTRAINT bank_connections_secret_ref_check CHECK (((secret_ref IS NULL) OR (secret_ref ~~ 'secret://cosa-connectors/%'::text)))
);

DO $$ BEGIN
  ALTER TABLE ONLY finance.bank_connections ADD CONSTRAINT bank_connections_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_connections_provider_account_unique ON finance.bank_connections USING btree (provider, provider_environment, provider_grant_id, external_account_id) WHERE ((provider_grant_id IS NOT NULL) AND (external_account_id IS NOT NULL) AND (consent_state <> 'REVOKED'::text));

CREATE INDEX IF NOT EXISTS idx_bank_connections_ws_provider ON finance.bank_connections USING btree (workspace_id, provider);


CREATE TABLE IF NOT EXISTS finance.bank_transactions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    bank_connection_id bigint NOT NULL,
    ingestion_event_id bigint,
    external_transaction_id text NOT NULL,
    posted_at timestamp with time zone NOT NULL,
    amount numeric(20,2) NOT NULL,
    currency text DEFAULT 'VND'::text NOT NULL,
    direction text NOT NULL,
    description text NOT NULL,
    counterparty_name text,
    counterparty_account text,
    status text DEFAULT 'UNRECONCILED'::text NOT NULL,
    matched_accounting_document_id bigint,
    raw_payload jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT bank_transactions_direction_check CHECK ((direction = ANY (ARRAY['IN'::text, 'OUT'::text]))),
    CONSTRAINT bank_transactions_status_check CHECK ((status = ANY (ARRAY['UNRECONCILED'::text, 'MATCHED'::text, 'CONFIRMED'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY finance.bank_transactions ADD CONSTRAINT bank_transactions_bank_connection_id_external_transaction_i_key UNIQUE (bank_connection_id, external_transaction_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY finance.bank_transactions ADD CONSTRAINT bank_transactions_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY finance.bank_transactions ADD CONSTRAINT bank_transactions_bank_connection_id_fkey FOREIGN KEY (bank_connection_id) REFERENCES finance.bank_connections(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_transactions_conn_ext_unique ON finance.bank_transactions USING btree (bank_connection_id, external_transaction_id);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_reconcile_status ON finance.bank_transactions USING btree (workspace_id, status);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_ws_posted ON finance.bank_transactions USING btree (workspace_id, posted_at);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_ws_status ON finance.bank_transactions USING btree (workspace_id, status);


CREATE TABLE IF NOT EXISTS finance.cas_link_sessions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    legal_entity_id bigint,
    created_by bigint NOT NULL,
    state_hash text NOT NULL,
    scopes jsonb DEFAULT '[]'::jsonb NOT NULL,
    allowed_redirect text NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    consumed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY finance.cas_link_sessions ADD CONSTRAINT cas_link_sessions_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY finance.cas_link_sessions ADD CONSTRAINT cas_link_sessions_state_hash_key UNIQUE (state_hash);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_cas_link_sessions_state_hash ON finance.cas_link_sessions USING btree (state_hash) WHERE (consumed_at IS NULL);

CREATE INDEX IF NOT EXISTS idx_cas_link_sessions_ws ON finance.cas_link_sessions USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS finance.cas_sync_inbox (
    id bigint NOT NULL,
    bank_connection_id bigint,
    provider text DEFAULT 'cas'::text NOT NULL,
    environment text DEFAULT 'sandbox'::text NOT NULL,
    source text NOT NULL,
    event_identity text NOT NULL,
    raw_payload jsonb NOT NULL,
    status text DEFAULT 'RECEIVED'::text NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    next_attempt_at timestamp with time zone DEFAULT now() NOT NULL,
    lease_until timestamp with time zone,
    lease_token text,
    error_code text,
    error_msg text,
    bank_transaction_id bigint,
    received_at timestamp with time zone DEFAULT now() NOT NULL,
    processed_at timestamp with time zone
);

DO $$ BEGIN
  ALTER TABLE ONLY finance.cas_sync_inbox ADD CONSTRAINT cas_sync_inbox_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY finance.cas_sync_inbox ADD CONSTRAINT cas_sync_inbox_bank_connection_id_fkey FOREIGN KEY (bank_connection_id) REFERENCES finance.bank_connections(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY finance.cas_sync_inbox ADD CONSTRAINT cas_sync_inbox_bank_transaction_id_fkey FOREIGN KEY (bank_transaction_id) REFERENCES finance.bank_transactions(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_cas_sync_inbox_conn ON finance.cas_sync_inbox USING btree (bank_connection_id, received_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cas_sync_inbox_dedup ON finance.cas_sync_inbox USING btree (provider, environment, event_identity);

CREATE INDEX IF NOT EXISTS idx_cas_sync_inbox_due ON finance.cas_sync_inbox USING btree (status, next_attempt_at, lease_until);


CREATE TABLE IF NOT EXISTS finance.cas_webhook_inbox (
    id bigint NOT NULL,
    provider_event_id text NOT NULL,
    raw_payload text NOT NULL,
    signature_header text,
    status text DEFAULT 'RECEIVED'::text NOT NULL,
    error_msg text,
    received_at timestamp with time zone DEFAULT now() NOT NULL,
    processed_at timestamp with time zone,
    CONSTRAINT cas_webhook_inbox_status_check CHECK ((status = ANY (ARRAY['RECEIVED'::text, 'PROCESSING'::text, 'PROCESSED'::text, 'FAILED'::text, 'DLQ'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY finance.cas_webhook_inbox ADD CONSTRAINT cas_webhook_inbox_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY finance.cas_webhook_inbox ADD CONSTRAINT cas_webhook_inbox_provider_event_id_key UNIQUE (provider_event_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_cas_webhook_inbox_status ON finance.cas_webhook_inbox USING btree (status, received_at);


CREATE TABLE IF NOT EXISTS finance.financial_transactions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    document_id bigint,
    project_id bigint,
    cycle_id bigint,
    work_item_id bigint,
    transaction_date date NOT NULL,
    description text NOT NULL,
    amount numeric(20,2) NOT NULL,
    direction text NOT NULL,
    category text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    idempotency_key text,
    approval_status text DEFAULT 'AUTO_APPROVED'::text NOT NULL,
    approved_by_user_id bigint,
    approved_at timestamp with time zone,
    provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    accounting_document_id bigint,
    currency text DEFAULT 'VND'::text NOT NULL,
    legal_entity_id bigint
);

DO $$ BEGIN
  ALTER TABLE ONLY finance.financial_transactions ADD CONSTRAINT financial_transactions_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY finance.financial_transactions ADD CONSTRAINT financial_transactions_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_financial_transactions_workspace_id ON finance.financial_transactions USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS finance.finance_exceptions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    transaction_id bigint,
    exception_type text NOT NULL,
    severity text DEFAULT 'WARNING'::text NOT NULL,
    details jsonb,
    status text DEFAULT 'OPEN'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

DO $$ BEGIN
  ALTER TABLE ONLY finance.finance_exceptions ADD CONSTRAINT finance_exceptions_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY finance.finance_exceptions ADD CONSTRAINT finance_exceptions_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES finance.financial_transactions(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_finance_exceptions_transaction_id ON finance.finance_exceptions USING btree (transaction_id);

CREATE INDEX IF NOT EXISTS idx_finance_exceptions_workspace_id ON finance.finance_exceptions USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS finance.financial_snapshots (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    snapshot_date date NOT NULL,
    cash_in numeric(20,2) DEFAULT 0 NOT NULL,
    cash_out numeric(20,2) DEFAULT 0 NOT NULL,
    net_burn numeric(20,2) DEFAULT 0 NOT NULL,
    runway_months numeric(6,2),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    opening_balance numeric(20,2) DEFAULT 0 NOT NULL,
    current_cash numeric(20,2),
    monthly_net_burn numeric(20,2),
    burn_window_months integer DEFAULT 3 NOT NULL,
    cash_flow_positive boolean DEFAULT false NOT NULL,
    currency text DEFAULT 'VND'::text NOT NULL,
    legal_entity_id bigint
);

DO $$ BEGIN
  ALTER TABLE ONLY finance.financial_snapshots ADD CONSTRAINT financial_snapshots_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE UNIQUE INDEX IF NOT EXISTS financial_snapshots_workspace_snapshot_currency_entity_key ON finance.financial_snapshots USING btree (workspace_id, snapshot_date, currency, COALESCE(legal_entity_id, (0)::bigint));

CREATE INDEX IF NOT EXISTS idx_financial_snapshots_ws_date ON finance.financial_snapshots USING btree (workspace_id, snapshot_date);


CREATE TABLE IF NOT EXISTS finance.project_budget_envelopes (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    legal_entity_id bigint NOT NULL,
    currency character varying(10) DEFAULT 'VND'::character varying NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    limit_minor numeric(38,0) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    owner_member_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

DO $$ BEGIN
  ALTER TABLE ONLY finance.project_budget_envelopes ADD CONSTRAINT project_budget_envelopes_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_budget_envelopes_project ON finance.project_budget_envelopes USING btree (project_id, period_start, period_end);



-- SP-A: restore the legal schema structure the 001 baseline squash dropped.
-- Bản squash baseline Founder Trial R1 (commit 81461673, `pg_dump --schema-only`)
-- gộp toàn bộ lịch sử migration finance-legal thành một file 001 và trong quá
-- trình đó KHÔNG tạo bảng legal.* nào. Runtime AI-compliance
-- (ai-compliance-access / ai-compliance-snapshot / ai-legal-applicability
-- services — nằm trên đường `resolve-data-use` gate mọi agent run) và 18 suite
-- vitest finance-legal cần các bảng này.
--
-- File này flatten phần DDL cấu trúc từ các migration đã bị xoá ở git ref
-- 81461673^:
--   - 12_legal_catalog                     (regulation catalog)
--   - 13_legal_applicability_obligations    (entity profiles, obligation templates/instances)
--   - 27_ai_compliance_governance           (13 bảng AI-compliance governance)
--   - 29_ai_compliance_runtime_hardening    (composite UNIQUE/FK + snapshot provenance columns)
--   - 30_ai_legal_source_corrections        (regulation_versions/evidence columns + ai_applicability_rules)
--   - 31_ai_legal_review_pending_correction (regulation_versions.legal_review_confirmed)
--
-- Ngoài 6 migration trên, 3 bảng dưới đây có trong
-- services/company/shared/db/schema/legal.ts nhưng nằm ở migration ngoài phạm vi
-- (23/32/34) — vẫn tạo lại ở đây để schema `legal` khớp đủ 23 export của
-- legal.ts (theo approach guidance của task brief):
--   - legal_verification_approvals  (từ 23_legal_verification_approvals)
--   - applicability_evaluations      (từ 32_legal_predicate_versions)
--   - obligation_transitions         (từ 34_obligation_lifecycle)
-- Và các cột do migration 33/34 thêm vào bảng đã có (workspace_ai_deployments,
-- legal_obligation_instances) cũng được thêm lại để khớp legal.ts.
--
-- CHỈ cấu trúc — KHÔNG seed nội dung regulation/rule (không INSERT/UPDATE/DELETE):
-- phần seed được cố ý hoãn sang task sau. Expand-only, idempotent (chạy lại
-- nhiều lần không lỗi): mọi CREATE TABLE/INDEX dùng IF NOT EXISTS, mọi
-- ADD CONSTRAINT bọc trong khối DO ... EXCEPTION WHEN duplicate_object.
--
-- Deviation duy nhất so với nguyên văn migration nguồn: bảng
-- legal.legal_entity_profiles KHÔNG có cột platform_company_id và KHÔNG có CHECK
-- trên cột status — cả hai đã bị 25_legal_entity_status_v2 (ngoài phạm vi) đổi;
-- legal.ts không model chúng nên theo quy tắc "Drizzle thắng khi bất đồng" ta
-- theo legal.ts.

CREATE SCHEMA IF NOT EXISTS legal;

-- =========================================================================
-- from 12_legal_catalog.up.sql — regulation sources & versions catalog
-- =========================================================================
CREATE TABLE IF NOT EXISTS legal.regulation_sources (
  id           BIGINT PRIMARY KEY,
  source_name  TEXT NOT NULL,
  issuer       TEXT NOT NULL,
  number       TEXT NOT NULL UNIQUE,
  url          TEXT NOT NULL,
  content_hash TEXT,
  layer        TEXT NOT NULL CHECK (layer IN ('CURRENT_LAW','POLICY_WATCH','PROFESSIONAL_REVIEW')),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS legal.regulation_versions (
  id                    BIGINT PRIMARY KEY,
  regulation_source_id  BIGINT NOT NULL REFERENCES legal.regulation_sources(id) ON DELETE CASCADE,
  version               TEXT NOT NULL,
  effective_from        DATE NOT NULL,
  effective_to          DATE,
  superseded_by_id      BIGINT REFERENCES legal.regulation_versions(id) ON DELETE SET NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (regulation_source_id, version)
);

CREATE INDEX IF NOT EXISTS idx_regulation_versions_source_effective
  ON legal.regulation_versions(regulation_source_id, effective_from);

-- from 30_ai_legal_source_corrections.up.sql §1 — cột thẩm định + provenance
ALTER TABLE legal.regulation_versions
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'ACTIVE',
  ADD COLUMN IF NOT EXISTS content_hash text,
  ADD COLUMN IF NOT EXISTS correction_reason text,
  ADD COLUMN IF NOT EXISTS artifact_path text,
  ADD COLUMN IF NOT EXISTS reviewer_member_id bigint,
  ADD COLUMN IF NOT EXISTS reviewed_at timestamp with time zone;

-- from 31_ai_legal_review_pending_correction.up.sql §1 — cờ xác nhận review pháp lý THẬT
ALTER TABLE legal.regulation_versions
  ADD COLUMN IF NOT EXISTS legal_review_confirmed boolean NOT NULL DEFAULT false;

-- =========================================================================
-- from 13_legal_applicability_obligations.up.sql — entity profiles, obligation
-- templates/instances, applicability rules
-- =========================================================================
-- Lưu ý: bỏ cột platform_company_id và CHECK trên status (25_legal_entity_status_v2
-- ngoài phạm vi đã đổi enum sang DRAFT|REGISTRATION_PREPARATION|
-- REGISTERED_UNVERIFIED|VERIFIED|SUSPENDED|DISSOLVED và drop platform_company_id).
-- legal.ts model status là `text NOT NULL DEFAULT 'DRAFT'` không CHECK — theo đó.
CREATE TABLE IF NOT EXISTS legal.legal_entity_profiles (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL,
  entity_type           TEXT NOT NULL,
  status                TEXT NOT NULL DEFAULT 'DRAFT',
  registration_number   TEXT,
  tax_id                TEXT,
  verified_by_member_id BIGINT,
  verified_at           TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_legal_entity_profiles_workspace
  ON legal.legal_entity_profiles(workspace_id);

-- from 23_legal_verification_approvals.up.sql — durable approval record cho legal
-- verification (bind workspace + entity + expected_status, expiry + separation-of-duty)
CREATE TABLE IF NOT EXISTS legal.legal_verification_approvals (
  id               BIGINT PRIMARY KEY,
  workspace_id     BIGINT NOT NULL,
  legal_entity_id  BIGINT NOT NULL REFERENCES legal.legal_entity_profiles(id) ON DELETE CASCADE,
  expected_status  TEXT NOT NULL,
  requested_by     BIGINT NOT NULL,
  approved_by      BIGINT,
  status           TEXT NOT NULL DEFAULT 'PENDING'
                     CHECK (status IN ('PENDING','APPROVED','REJECTED','EXPIRED')),
  requested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  decided_at       TIMESTAMPTZ,
  expires_at       TIMESTAMPTZ NOT NULL,
  rationale        TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_legal_verification_approvals_pending
  ON legal.legal_verification_approvals (workspace_id, legal_entity_id, expected_status)
  WHERE status = 'PENDING';
CREATE INDEX IF NOT EXISTS idx_legal_verification_approvals_ws_entity
  ON legal.legal_verification_approvals (workspace_id, legal_entity_id);

CREATE TABLE IF NOT EXISTS legal.legal_obligation_templates (
  id                       BIGINT PRIMARY KEY,
  regulation_version_id    BIGINT NOT NULL REFERENCES legal.regulation_versions(id) ON DELETE CASCADE,
  title                    TEXT NOT NULL,
  description              TEXT,
  typical_due_offset_days  INTEGER,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS legal.applicability_rules (
  id                       BIGINT PRIMARY KEY,
  regulation_version_id    BIGINT NOT NULL REFERENCES legal.regulation_versions(id) ON DELETE CASCADE,
  predicate                JSONB NOT NULL,
  obligation_template_id   BIGINT NOT NULL REFERENCES legal.legal_obligation_templates(id) ON DELETE CASCADE,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- from 32_legal_predicate_versions.up.sql — persisted applicability evaluations
CREATE TABLE IF NOT EXISTS legal.applicability_evaluations (
  id               BIGINT PRIMARY KEY,
  workspace_id     BIGINT NOT NULL,
  legal_entity_id  BIGINT NOT NULL,
  rule_id          BIGINT NOT NULL,
  rule_version     TEXT NOT NULL DEFAULT '1.0',
  facts_version    TEXT NOT NULL DEFAULT '1.0',
  result           TEXT NOT NULL,
  reason_codes     JSONB NOT NULL DEFAULT '[]'::jsonb,
  evaluated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_ref       TEXT,
  CONSTRAINT uq_entity_rule_facts_version UNIQUE (legal_entity_id, rule_id, facts_version)
);
CREATE INDEX IF NOT EXISTS idx_applicability_eval_ws_entity
  ON legal.applicability_evaluations(workspace_id, legal_entity_id);

CREATE TABLE IF NOT EXISTS legal.legal_obligation_instances (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  legal_entity_profile_id    BIGINT REFERENCES legal.legal_entity_profiles(id) ON DELETE SET NULL,
  template_id                BIGINT REFERENCES legal.legal_obligation_templates(id) ON DELETE SET NULL,
  regulation_version_id      BIGINT REFERENCES legal.regulation_versions(id) ON DELETE SET NULL,
  source                     TEXT NOT NULL CHECK (source IN ('REGULATION_TEMPLATE','USER_CREATED','AI_PROPOSAL')),
  title                      TEXT NOT NULL,
  due_date                   DATE,
  status                     TEXT NOT NULL DEFAULT 'OPEN',
  evidence_artifact_id       BIGINT,
  applicability_assessed_at  TIMESTAMPTZ,
  owner_member_id            BIGINT,
  review_status              TEXT NOT NULL DEFAULT 'PENDING',
  legacy_ref                 TEXT UNIQUE,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_legal_obligation_instances_workspace_status
  ON legal.legal_obligation_instances(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_legal_obligation_instances_workspace_due
  ON legal.legal_obligation_instances(workspace_id, due_date);

-- from 34_obligation_lifecycle.up.sql — cột lifecycle + idempotency index +
-- bảng audit trail chuyển trạng thái obligation
ALTER TABLE legal.legal_obligation_instances
  ADD COLUMN IF NOT EXISTS period_key TEXT,
  ADD COLUMN IF NOT EXISTS evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS uq_legal_obligation_period_entity
  ON legal.legal_obligation_instances (workspace_id, template_id, period_key, COALESCE(legal_entity_profile_id, 0))
  WHERE template_id IS NOT NULL AND period_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS legal.obligation_transitions (
  id                     BIGINT PRIMARY KEY,
  workspace_id           BIGINT NOT NULL,
  obligation_instance_id BIGINT NOT NULL REFERENCES legal.legal_obligation_instances(id) ON DELETE CASCADE,
  from_status            TEXT NOT NULL,
  to_status              TEXT NOT NULL,
  evidence_artifact_id   BIGINT,
  evidence_refs          JSONB NOT NULL DEFAULT '[]'::jsonb,
  actor_member_id        BIGINT,
  rationale              TEXT,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_obligation_transitions_instance
  ON legal.obligation_transitions (obligation_instance_id, created_at DESC);

-- =========================================================================
-- from 27_ai_compliance_governance.up.sql — AI compliance & governance
-- (13 bảng, reproduce nguyên văn — đã là CREATE TABLE IF NOT EXISTS)
-- =========================================================================
CREATE TABLE IF NOT EXISTS legal.ai_system_catalog (
  id                         BIGINT PRIMARY KEY,
  system_key                 TEXT NOT NULL UNIQUE,
  name                       TEXT NOT NULL,
  allowed_purposes           JSONB NOT NULL DEFAULT '[]'::jsonb,
  prohibited_purposes        JSONB NOT NULL DEFAULT '[]'::jsonb,
  technical_owner_member_id  BIGINT,
  lifecycle_status           TEXT NOT NULL DEFAULT 'DRAFT' CHECK (lifecycle_status IN ('DRAFT','ACTIVE','DEPRECATED','RETIRED')),
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS legal.ai_system_versions (
  id                         BIGINT PRIMARY KEY,
  system_catalog_id          BIGINT NOT NULL REFERENCES legal.ai_system_catalog(id) ON DELETE CASCADE,
  version                    TEXT NOT NULL,
  config_hash                TEXT NOT NULL,
  model_profile_ref          TEXT,
  status                     TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','ACTIVE','DEPRECATED','RETIRED')),
  released_at                TIMESTAMPTZ,
  deprecated_at              TIMESTAMPTZ,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (system_catalog_id, version)
);
CREATE INDEX IF NOT EXISTS idx_ai_system_versions_catalog
  ON legal.ai_system_versions (system_catalog_id);

CREATE TABLE IF NOT EXISTS legal.workspace_ai_deployments (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  system_version_id          BIGINT NOT NULL REFERENCES legal.ai_system_versions(id),
  mode                       TEXT NOT NULL CHECK (mode = 'ADVISORY_ONLY'),
  status                     TEXT NOT NULL CHECK (status IN ('DRAFT','ASSESSED','APPROVED_FOR_USE','SUSPENDED','REJECTED','RETIRED')),
  founder_member_id          BIGINT NOT NULL,
  technical_owner_member_id  BIGINT,
  current_assessment_id      BIGINT,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS workspace_ai_deployments_workspace_status_idx
  ON legal.workspace_ai_deployments (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_workspace_ai_deployments_workspace
  ON legal.workspace_ai_deployments (workspace_id);

-- from 33_deployment_authority_versions.up.sql — workforce authority + policy versioning
ALTER TABLE legal.workspace_ai_deployments
  ADD COLUMN IF NOT EXISTS created_by_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS accountable_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS reviewer_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS approved_by_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS policy_version INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS approved_version INTEGER;

CREATE TABLE IF NOT EXISTS legal.ai_system_capability_bindings (
  id                         BIGINT PRIMARY KEY,
  system_version_id          BIGINT NOT NULL REFERENCES legal.ai_system_versions(id) ON DELETE CASCADE,
  capability_id              TEXT NOT NULL,
  effect_class               TEXT NOT NULL CHECK (effect_class IN ('READ','DRAFT','EXTERNAL')),
  decision_domain            TEXT NOT NULL CHECK (decision_domain IN ('GENERAL','LEGAL','FINANCE','HR','OPERATIONS','COMMERCIAL')),
  requires_human_confirmation BOOLEAN NOT NULL DEFAULT true,
  may_send_to_model          BOOLEAN NOT NULL DEFAULT false,
  max_data_category          TEXT NOT NULL CHECK (max_data_category IN ('NON_PERSONAL','PERSONAL','SENSITIVE_PERSONAL','BUSINESS_CONFIDENTIAL')),
  action_recipient_scope     TEXT,
  prohibited_purpose         BOOLEAN NOT NULL DEFAULT false,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (system_version_id, capability_id)
);
CREATE INDEX IF NOT EXISTS idx_ai_capability_bindings_version
  ON legal.ai_system_capability_bindings (system_version_id);

CREATE TABLE IF NOT EXISTS legal.ai_risk_assessments (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  deployment_id              BIGINT NOT NULL REFERENCES legal.workspace_ai_deployments(id) ON DELETE CASCADE,
  classification             TEXT NOT NULL CHECK (classification IN ('OUT_OF_CATALOG','REQUIRES_REVIEW','HIGH_RISK')),
  intended_purpose           TEXT NOT NULL,
  affected_stakeholders      JSONB NOT NULL DEFAULT '[]'::jsonb,
  controls                   JSONB NOT NULL DEFAULT '[]'::jsonb,
  reviewer_member_id         BIGINT,
  approved_by_member_id      BIGINT,
  approved_at                TIMESTAMPTZ,
  rationale                  TEXT,
  expires_at                 TIMESTAMPTZ NOT NULL,
  status                     TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','APPROVED','REJECTED','EXPIRED')),
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_risk_assessments_workspace_deployment_idx
  ON legal.ai_risk_assessments (workspace_id, deployment_id);
CREATE INDEX IF NOT EXISTS idx_ai_risk_assessments_workspace
  ON legal.ai_risk_assessments (workspace_id);

-- deferred single-column FK (27_ai_compliance_governance): workspace_ai_deployments
-- .current_assessment_id -> ai_risk_assessments(id); thêm sau khi cả hai bảng tồn tại.
DO $$ BEGIN
  ALTER TABLE legal.workspace_ai_deployments
    ADD CONSTRAINT fk_workspace_ai_deployments_assessment
    FOREIGN KEY (current_assessment_id)
    REFERENCES legal.ai_risk_assessments(id)
    ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS legal.ai_compliance_evidence (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  assessment_id              BIGINT NOT NULL REFERENCES legal.ai_risk_assessments(id) ON DELETE CASCADE,
  evidence_type              TEXT NOT NULL,
  uri_reference              TEXT NOT NULL,
  content_hash               TEXT NOT NULL,
  checked_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewer_member_id         BIGINT NOT NULL,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_compliance_evidence_workspace_assessment_idx
  ON legal.ai_compliance_evidence (workspace_id, assessment_id);
CREATE INDEX IF NOT EXISTS idx_ai_compliance_evidence_workspace
  ON legal.ai_compliance_evidence (workspace_id);

-- from 30_ai_legal_source_corrections.up.sql §2 — cột kết luận + nguồn
ALTER TABLE legal.ai_compliance_evidence
  ADD COLUMN IF NOT EXISTS conclusion text NOT NULL DEFAULT 'COMPLIANT',
  ADD COLUMN IF NOT EXISTS source_version_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS rule_ids jsonb NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS legal.ai_provider_profiles (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  provider_key               TEXT NOT NULL,
  model_key                  TEXT NOT NULL,
  version                    TEXT NOT NULL,
  status                     TEXT NOT NULL CHECK (status IN ('DRAFT','APPROVED','SUSPENDED','REVOKED')),
  declared_processing_region TEXT NOT NULL,
  dpa_reference              TEXT,
  allowed_data_categories    JSONB NOT NULL DEFAULT '[]'::jsonb,
  reviewed_at                TIMESTAMPTZ,
  reviewed_by_member_id      BIGINT,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, provider_key, model_key, version)
);
CREATE INDEX IF NOT EXISTS ai_provider_profiles_workspace_status_idx
  ON legal.ai_provider_profiles (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_ai_provider_profiles_workspace
  ON legal.ai_provider_profiles (workspace_id);

CREATE TABLE IF NOT EXISTS legal.ai_data_processing_profiles (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  deployment_id              BIGINT NOT NULL REFERENCES legal.workspace_ai_deployments(id) ON DELETE CASCADE,
  binding_id                 BIGINT REFERENCES legal.ai_system_capability_bindings(id) ON DELETE SET NULL,
  purpose_id                 TEXT NOT NULL,
  data_categories            JSONB NOT NULL DEFAULT '[]'::jsonb,
  recipient_provider_profile_id BIGINT REFERENCES legal.ai_provider_profiles(id) ON DELETE RESTRICT,
  retention_policy_id        TEXT NOT NULL,
  transfer_conditions        JSONB NOT NULL DEFAULT '[]'::jsonb,
  minimization_required      BOOLEAN NOT NULL DEFAULT true,
  version                    TEXT NOT NULL,
  status                     TEXT NOT NULL CHECK (status IN ('DRAFT','ACTIVE','SUSPENDED','RETIRED')),
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_data_processing_profiles_workspace_deployment_idx
  ON legal.ai_data_processing_profiles (workspace_id, deployment_id);
CREATE INDEX IF NOT EXISTS idx_ai_data_processing_profiles_workspace
  ON legal.ai_data_processing_profiles (workspace_id);

CREATE TABLE IF NOT EXISTS legal.data_processing_authorizations (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  subject_reference_hash     TEXT NOT NULL,
  purpose_id                 TEXT NOT NULL,
  purpose_version            TEXT NOT NULL,
  authority_type             TEXT NOT NULL CHECK (authority_type IN ('CONSENT','CONTRACTUAL_NECESSITY','LEGAL_OBLIGATION','VITAL_INTERESTS','LEGITIMATE_INTERESTS')),
  proof_reference            TEXT NOT NULL,
  proof_hash                 TEXT NOT NULL,
  status                     TEXT NOT NULL CHECK (status IN ('GRANTED','WITHDRAWN','RESTRICTED')),
  granted_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  withdrawn_at               TIMESTAMPTZ,
  restricted_at              TIMESTAMPTZ,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS data_processing_authorizations_workspace_subject_idx
  ON legal.data_processing_authorizations (workspace_id, subject_reference_hash);
CREATE INDEX IF NOT EXISTS idx_data_processing_authorizations_workspace
  ON legal.data_processing_authorizations (workspace_id);

CREATE TABLE IF NOT EXISTS legal.data_subject_requests (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  subject_reference_hash     TEXT NOT NULL,
  request_type               TEXT NOT NULL CHECK (request_type IN ('ACCESS','CORRECTION','DELETION','RESTRICTION')),
  deadline                   TIMESTAMPTZ NOT NULL,
  status                     TEXT NOT NULL CHECK (status IN ('RECEIVED','IN_REVIEW','FULFILLED','REJECTED','LEGAL_HOLD')),
  result_summary             TEXT,
  legal_hold                 BOOLEAN NOT NULL DEFAULT false,
  legal_hold_reason          TEXT,
  handled_by_member_id       BIGINT,
  resolved_at                TIMESTAMPTZ,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS data_subject_requests_workspace_status_idx
  ON legal.data_subject_requests (workspace_id, status);
CREATE INDEX IF NOT EXISTS data_subject_requests_workspace_subject_idx
  ON legal.data_subject_requests (workspace_id, subject_reference_hash);
CREATE INDEX IF NOT EXISTS idx_data_subject_requests_workspace
  ON legal.data_subject_requests (workspace_id);

CREATE TABLE IF NOT EXISTS legal.ai_incidents (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  deployment_id              BIGINT NOT NULL REFERENCES legal.workspace_ai_deployments(id) ON DELETE CASCADE,
  severity                   TEXT NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
  status                     TEXT NOT NULL CHECK (status IN ('OPEN','CONTAINED','ASSESSING','NOTIFICATION_DECISION_PENDING','REMEDIATING','CLOSED')),
  detected_at                TIMESTAMPTZ NOT NULL,
  contained_at               TIMESTAMPTZ,
  closed_at                  TIMESTAMPTZ,
  data_categories            JSONB NOT NULL DEFAULT '[]'::jsonb,
  notification_deadline      TIMESTAMPTZ,
  notification_decision      TEXT CHECK (notification_decision IN ('NOT_REQUIRED','NOTIFY_AUTHORITY','NOTIFY_SUBJECTS','NOTIFY_BOTH')),
  notification_decision_at   TIMESTAMPTZ,
  notification_decision_by_member_id BIGINT,
  notification_rationale     TEXT,
  summary                    TEXT NOT NULL,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_incidents_workspace_deployment_idx
  ON legal.ai_incidents (workspace_id, deployment_id);
CREATE INDEX IF NOT EXISTS ai_incidents_workspace_status_idx
  ON legal.ai_incidents (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_ai_incidents_workspace
  ON legal.ai_incidents (workspace_id);

CREATE TABLE IF NOT EXISTS legal.ai_incident_actions (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  incident_id                BIGINT NOT NULL REFERENCES legal.ai_incidents(id) ON DELETE CASCADE,
  action_type                TEXT NOT NULL,
  description                TEXT NOT NULL,
  taken_by_member_id         BIGINT NOT NULL,
  evidence_reference         TEXT,
  evidence_hash              TEXT,
  taken_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_incident_actions_workspace_incident_idx
  ON legal.ai_incident_actions (workspace_id, incident_id);
CREATE INDEX IF NOT EXISTS idx_ai_incident_actions_workspace
  ON legal.ai_incident_actions (workspace_id);

CREATE TABLE IF NOT EXISTS legal.ai_compliance_snapshots (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  deployment_id              BIGINT NOT NULL REFERENCES legal.workspace_ai_deployments(id) ON DELETE CASCADE,
  assessment_id              BIGINT NOT NULL REFERENCES legal.ai_risk_assessments(id) ON DELETE CASCADE,
  mode                       TEXT NOT NULL CHECK (mode = 'ADVISORY_ONLY'),
  status                     TEXT NOT NULL CHECK (status IN ('DRAFT','ASSESSED','APPROVED_FOR_USE','SUSPENDED','REJECTED','RETIRED')),
  allowed_capabilities       JSONB NOT NULL DEFAULT '[]'::jsonb,
  provider_profile_version   TEXT NOT NULL,
  data_profile_version       TEXT NOT NULL,
  legal_version_ids          JSONB NOT NULL DEFAULT '[]'::jsonb,
  policy_snapshot_hash       TEXT NOT NULL,
  snapshot_hash              TEXT NOT NULL UNIQUE,
  issued_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at                 TIMESTAMPTZ NOT NULL,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_compliance_snapshots_workspace_deployment_idx
  ON legal.ai_compliance_snapshots (workspace_id, deployment_id);
CREATE INDEX IF NOT EXISTS ai_compliance_snapshots_workspace_hash_idx
  ON legal.ai_compliance_snapshots (workspace_id, snapshot_hash);
CREATE INDEX IF NOT EXISTS idx_ai_compliance_snapshots_workspace
  ON legal.ai_compliance_snapshots (workspace_id);

-- =========================================================================
-- from 30_ai_legal_source_corrections.up.sql §3 — ai_applicability_rules
-- (bảng quy tắc áp dụng AI chính quy gắn nguồn luật đã thẩm định)
-- =========================================================================
CREATE TABLE IF NOT EXISTS legal.ai_applicability_rules (
  id bigint PRIMARY KEY,
  rule_id text NOT NULL UNIQUE,
  rule_version text NOT NULL DEFAULT '1.0.0',
  regulation_source_id bigint NOT NULL REFERENCES legal.regulation_sources(id) ON DELETE CASCADE,
  regulation_version_id bigint NOT NULL REFERENCES legal.regulation_versions(id) ON DELETE CASCADE,
  source_content_hash text NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  review_status text NOT NULL DEFAULT 'REVIEWED',
  layer text NOT NULL,
  effect text NOT NULL,
  reason_code text NOT NULL,
  description text,
  predicate jsonb NOT NULL,
  mandatory_evidence_type text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

-- =========================================================================
-- from 29_ai_compliance_runtime_hardening.up.sql — defense-in-depth ở tầng DB
-- cho quyền sở hữu theo workspace. Nguyên tắc: composite UNIQUE (workspace_id, id)
-- trên bảng cha thuộc workspace + composite FK (workspace_id, <ref>) trên bảng
-- con -> PostgreSQL tự chặn insert/update cross-workspace.
--
-- Khác nguyên văn migration 29: bỏ NOT VALID + cặp VALIDATE CONSTRAINT (DB
-- baseline mới hoàn toàn rỗng, không có row lịch sử cần bỏ qua) và bỏ toàn bộ
-- backfill UPDATE — chỉ giữ phần cấu trúc.
-- =========================================================================

-- 1. Composite unique key trên các bảng cha thuộc workspace.
DO $$ BEGIN ALTER TABLE legal.workspace_ai_deployments ADD CONSTRAINT workspace_ai_deployments_workspace_id_id_key UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_risk_assessments ADD CONSTRAINT ai_risk_assessments_workspace_id_id_key UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_provider_profiles ADD CONSTRAINT ai_provider_profiles_workspace_id_id_key UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_incidents ADD CONSTRAINT ai_incidents_workspace_id_id_key UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_data_processing_profiles ADD CONSTRAINT ai_data_processing_profiles_workspace_id_id_key UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

-- 2. Composite foreign key trên bảng con -> parent(workspace_id, id).
DO $$ BEGIN ALTER TABLE legal.ai_risk_assessments ADD CONSTRAINT ai_risk_assessments_workspace_deployment_fk FOREIGN KEY (workspace_id, deployment_id) REFERENCES legal.workspace_ai_deployments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.workspace_ai_deployments ADD CONSTRAINT workspace_ai_deployments_workspace_assessment_fk FOREIGN KEY (workspace_id, current_assessment_id) REFERENCES legal.ai_risk_assessments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_evidence ADD CONSTRAINT ai_compliance_evidence_workspace_assessment_fk FOREIGN KEY (workspace_id, assessment_id) REFERENCES legal.ai_risk_assessments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_data_processing_profiles ADD CONSTRAINT ai_data_profiles_workspace_deployment_fk FOREIGN KEY (workspace_id, deployment_id) REFERENCES legal.workspace_ai_deployments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_data_processing_profiles ADD CONSTRAINT ai_data_profiles_workspace_provider_fk FOREIGN KEY (workspace_id, recipient_provider_profile_id) REFERENCES legal.ai_provider_profiles (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_incidents ADD CONSTRAINT ai_incidents_workspace_deployment_fk FOREIGN KEY (workspace_id, deployment_id) REFERENCES legal.workspace_ai_deployments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_incident_actions ADD CONSTRAINT ai_incident_actions_workspace_incident_fk FOREIGN KEY (workspace_id, incident_id) REFERENCES legal.ai_incidents (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_snapshots ADD CONSTRAINT ai_compliance_snapshots_workspace_deployment_fk FOREIGN KEY (workspace_id, deployment_id) REFERENCES legal.workspace_ai_deployments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_snapshots ADD CONSTRAINT ai_compliance_snapshots_workspace_assessment_fk FOREIGN KEY (workspace_id, assessment_id) REFERENCES legal.ai_risk_assessments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

-- 3. Snapshot provenance columns (migration 29 §3) — id thật của binding/evidence/
-- provider profile/data profile đã dùng để tạo snapshot + cờ provenance_complete.
ALTER TABLE legal.ai_compliance_snapshots
  ADD COLUMN IF NOT EXISTS capability_binding_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS evidence_hashes JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS provider_profile_id BIGINT,
  ADD COLUMN IF NOT EXISTS data_profile_id BIGINT,
  ADD COLUMN IF NOT EXISTS provenance_complete BOOLEAN NOT NULL DEFAULT false;

DO $$ BEGIN ALTER TABLE legal.ai_compliance_snapshots ADD CONSTRAINT ai_compliance_snapshots_workspace_provider_fk FOREIGN KEY (workspace_id, provider_profile_id) REFERENCES legal.ai_provider_profiles (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_snapshots ADD CONSTRAINT ai_compliance_snapshots_workspace_data_profile_fk FOREIGN KEY (workspace_id, data_profile_id) REFERENCES legal.ai_data_processing_profiles (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


-- SP-A Task 5C — Khôi phục 20 bảng `finance.*` bị bỏ rơi trong đợt squash
-- baseline Founder Trial R1 (`pg_dump --schema-only`, commit 81461673).
--
-- Bản squash gộp toàn bộ lịch sử migration finance-legal thành một file `001`
-- nhưng chỉ tạo 9 / 29 bảng `finance.*` mà
-- `services/company/shared/db/schema/finance-legal.ts` khai báo. `finance` là
-- schema RETAINED của R1 và Drizzle schema là nguồn sự thật R1 (quyết định
-- người dùng 2026-09-10) — file này tạo lại 20 bảng còn thiếu:
--
--   accounting_book_entries, accounting_coa_mappings, accounting_documents,
--   accounting_fiscal_profiles, accounting_mapping_confirmations,
--   accounting_periods, accounting_policies, accounting_profiles,
--   accounting_regime_policies, accounting_regime_transition_logs,
--   accounting_report_mappings, accounting_report_snapshots, cas_normalizer_log,
--   document_reconciliation_proposals, finance_management_snapshots,
--   ingestion_dlq, ingestion_events, payment_allocations, payment_requests,
--   tax_obligation_instances
--
-- Nguồn DDL: schema-only `pg_dump` của DB dev `workspace` (còn giữ nguyên schema
-- pre-squash đầy đủ) — được reset spec §7.3 cho phép dùng làm "comparison aid
-- for constraints and indexes". Cột / kiểu / DEFAULT / NOT NULL / CHECK sao chép
-- verbatim từ dump; đã đối chiếu ~8 bảng với `finance-legal.ts` (Drizzle thắng
-- khi bất đồng — không có bất đồng nào phát hiện).
--
-- Expand-only + idempotent: mọi `CREATE TABLE`/`CREATE INDEX` dùng
-- `IF NOT EXISTS`; mọi `ADD CONSTRAINT` bọc trong khối `DO ... EXCEPTION WHEN
-- duplicate_object / duplicate_table THEN NULL`. Không INSERT/UPDATE/DELETE,
-- không DROP/RENAME/TRUNCATE, không SET NOT NULL trên cột đã có.
--
-- PK `id bigint` do app cấp (Snowflake) — dump KHÔNG có IDENTITY / nextval
-- default nào, khớp `finance-legal.ts` (`.primaryKey()` không
-- `.generatedAlwaysAsIdentity()`). Sequence orphan trong dump (không nối vào
-- cột) bị bỏ.
--
-- Deviation duy nhất so với dump: 2 FK trỏ `legal.regulation_versions(id)` bị
-- BỎ —
--   * accounting_profiles.regulation_version_id
--   * accounting_regime_policies.regulation_version_id
-- Lý do: `legal.regulation_versions` KHÔNG do finance-legal/`001` tạo (chỉ có ở
-- `002_restore_baseline_gaps`, thuộc Task 1) và Task 5C độc lập với `002`.
-- Drizzle `finance-legal.ts` cũng KHÔNG khai báo `.references()` cho 2 cột này
-- (accountingProfiles.regulationVersionId / accountingRegimePolicies
-- .regulationVersionId là `bigint` trần) nên cấu trúc dưới đây vẫn khớp Drizzle.

-- =========================================================================
-- 1. CREATE TABLE (20 bảng còn thiếu, đã sắp bảng cha trước bảng con)
-- =========================================================================

CREATE TABLE IF NOT EXISTS finance.accounting_fiscal_profiles (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    fiscal_year integer NOT NULL,
    regulation_code character varying(50) DEFAULT 'TT58_2026'::character varying NOT NULL,
    mode character varying(50) DEFAULT 'TT58_MODE_1'::character varying NOT NULL,
    status character varying(30) DEFAULT 'ACTIVE'::character varying NOT NULL,
    locked_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    legal_entity_id bigint,
    year_end date,
    mapping_version character varying(50),
    applicability_decision_id bigint
);

CREATE TABLE IF NOT EXISTS finance.accounting_periods (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    status text DEFAULT 'OPEN'::text NOT NULL,
    closed_by bigint,
    closed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    idempotency_key text,
    legal_entity_id bigint,
    fiscal_profile_id bigint,
    version integer DEFAULT 1 NOT NULL
);

CREATE TABLE IF NOT EXISTS finance.accounting_regime_policies (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    regulation_version_id bigint NOT NULL,
    mode text NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    requires_coa boolean DEFAULT false NOT NULL,
    requires_double_entry boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS finance.accounting_documents (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    document_type text NOT NULL,
    number text NOT NULL,
    document_date date NOT NULL,
    amount numeric(20,2) NOT NULL,
    currency text DEFAULT 'VND'::text NOT NULL,
    description text NOT NULL,
    status text DEFAULT 'DRAFT'::text NOT NULL,
    regime_policy_id bigint,
    line_items jsonb DEFAULT '[]'::jsonb NOT NULL,
    confirmed_at timestamp with time zone,
    confirmed_by bigint,
    void_reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT accounting_documents_document_type_check CHECK ((document_type = ANY (ARRAY['RECEIPT'::text, 'PAYMENT'::text, 'INVOICE'::text, 'JOURNAL'::text]))),
    CONSTRAINT accounting_documents_status_check CHECK ((status = ANY (ARRAY['DRAFT'::text, 'CONFIRMED'::text, 'VOID'::text])))
);

CREATE TABLE IF NOT EXISTS finance.accounting_book_entries (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    legal_entity_id bigint NOT NULL,
    period_id bigint NOT NULL,
    document_id bigint,
    item text NOT NULL,
    category character varying(30) NOT NULL,
    amount_minor numeric(38,0) NOT NULL,
    currency character varying(10) DEFAULT 'VND'::character varying NOT NULL,
    effective_date date NOT NULL,
    source text NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS finance.accounting_report_snapshots (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    legal_entity_id bigint NOT NULL,
    period_id bigint NOT NULL,
    report_code character varying(10) NOT NULL,
    mapping_version character varying(50) NOT NULL,
    input_watermark text NOT NULL,
    lines jsonb DEFAULT '[]'::jsonb NOT NULL,
    status character varying(20) NOT NULL,
    issues jsonb DEFAULT '[]'::jsonb NOT NULL,
    generated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS finance.accounting_coa_mappings (
    id bigint NOT NULL,
    source_regulation character varying(50) NOT NULL,
    target_regulation character varying(50) NOT NULL,
    source_account_code character varying(50) NOT NULL,
    target_account_code character varying(50) NOT NULL,
    mapping_type character varying(30) DEFAULT 'DIRECT_1_1'::character varying NOT NULL,
    description character varying(255)
);

CREATE TABLE IF NOT EXISTS finance.accounting_mapping_confirmations (
    id bigint NOT NULL,
    regime_code character varying(50) NOT NULL,
    mapping_version character varying(50) NOT NULL,
    confirmed_by_member_id bigint NOT NULL,
    confirmed_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS finance.accounting_policies (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    legal_entity_id bigint NOT NULL,
    inventory_valuation_method character varying(50) DEFAULT 'weighted_average'::character varying NOT NULL,
    depreciation_method character varying(50) DEFAULT 'straight_line'::character varying NOT NULL,
    revenue_recognition_method text DEFAULT 'Ghi nhận khi hoàn thành chuyển giao dịch vụ/hàng hóa'::text NOT NULL,
    corporate_income_tax_rate_bps integer,
    confirmed_by_member_id bigint,
    confirmed_at timestamp with time zone,
    version integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS finance.accounting_profiles (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    mode text DEFAULT 'TT58_MODE_1'::text NOT NULL,
    status text DEFAULT 'DRAFT'::text NOT NULL,
    confirmed_by bigint,
    confirmed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    regulation_version_id bigint,
    applicability_confirmed_at timestamp with time zone,
    applicability_confirmed_by bigint
);

CREATE TABLE IF NOT EXISTS finance.accounting_regime_transition_logs (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    from_fiscal_year integer NOT NULL,
    to_fiscal_year integer NOT NULL,
    from_regulation character varying(50) NOT NULL,
    to_regulation character varying(50) NOT NULL,
    cutoff_date date NOT NULL,
    is_balanced boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS finance.accounting_report_mappings (
    id bigint NOT NULL,
    regime_code character varying(50) NOT NULL,
    mapping_version character varying(50) NOT NULL,
    report_code character varying(10) NOT NULL,
    line_code character varying(20) NOT NULL,
    official_code character varying(50) NOT NULL,
    name text NOT NULL,
    source_ref text NOT NULL,
    rule_type character varying(20) NOT NULL,
    bucket character varying(20),
    sign smallint NOT NULL,
    rounding character varying(20) NOT NULL,
    definition_hash text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    derived_kind character varying(30)
);

CREATE TABLE IF NOT EXISTS finance.tax_obligation_instances (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    legal_entity_id bigint NOT NULL,
    period_id bigint NOT NULL,
    tax_name character varying(100) NOT NULL,
    incurred_minor numeric(38,0) DEFAULT 0 NOT NULL,
    paid_minor numeric(38,0) DEFAULT 0 NOT NULL,
    source character varying(20) DEFAULT 'MANUAL'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS finance.cas_normalizer_log (
    id bigint NOT NULL,
    bank_connection_id bigint NOT NULL,
    inbox_event_id bigint,
    provider_tx_id text NOT NULL,
    provider_tx_hash text NOT NULL,
    bank_transaction_id bigint,
    action text DEFAULT 'INSERT'::text NOT NULL,
    fail_reason text,
    normalized_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS finance.document_reconciliation_proposals (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    bank_transaction_id bigint NOT NULL,
    accounting_document_id bigint NOT NULL,
    confidence numeric(5,4) NOT NULL,
    candidate_match jsonb DEFAULT '{}'::jsonb NOT NULL,
    status text DEFAULT 'PENDING'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    accepted_by bigint,
    accepted_at timestamp with time zone,
    CONSTRAINT document_reconciliation_proposals_status_check CHECK ((status = ANY (ARRAY['PENDING'::text, 'ACCEPTED'::text, 'REJECTED'::text])))
);

CREATE TABLE IF NOT EXISTS finance.finance_management_snapshots (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    cycle_id bigint,
    as_of date NOT NULL,
    cash numeric(20,2) NOT NULL,
    burn numeric(20,2) NOT NULL,
    runway_months numeric(12,2),
    revenue numeric(20,2) DEFAULT 0 NOT NULL,
    expenses numeric(20,2) DEFAULT 0 NOT NULL,
    budget_variance numeric(20,2),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS finance.ingestion_dlq (
    id bigint NOT NULL,
    inbox_event_id bigint NOT NULL,
    bank_connection_id bigint,
    moved_at timestamp with time zone DEFAULT now() NOT NULL,
    fail_count integer DEFAULT 0 NOT NULL,
    last_error text,
    reviewed boolean DEFAULT false NOT NULL,
    reviewed_at timestamp with time zone,
    reviewed_by bigint
);

CREATE TABLE IF NOT EXISTS finance.ingestion_events (
    id bigint NOT NULL,
    bank_connection_id bigint NOT NULL,
    provider_event_id text NOT NULL,
    received_at timestamp with time zone DEFAULT now() NOT NULL,
    raw_payload_ref text,
    checksum text,
    status text DEFAULT 'RECEIVED'::text NOT NULL,
    error_msg text,
    processed_at timestamp with time zone,
    CONSTRAINT ingestion_events_status_check CHECK ((status = ANY (ARRAY['RECEIVED'::text, 'PROCESSING'::text, 'PROCESSED'::text, 'FAILED'::text, 'DLQ'::text])))
);

CREATE TABLE IF NOT EXISTS finance.payment_requests (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    legal_entity_id bigint NOT NULL,
    project_id bigint,
    owner_member_id bigint,
    amount_minor numeric(38,0) NOT NULL,
    currency text DEFAULT 'VND'::text NOT NULL,
    beneficiary_bank_bin text NOT NULL,
    beneficiary_account_number text NOT NULL,
    beneficiary_name text NOT NULL,
    purpose text NOT NULL,
    document_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    due_at timestamp with time zone,
    transfer_reference text,
    approval_state text DEFAULT 'DRAFT'::text NOT NULL,
    settlement_state text DEFAULT 'UNPAID'::text NOT NULL,
    accounting_state text DEFAULT 'UNCLASSIFIED'::text NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    approval_hash text,
    approved_version integer,
    approved_by_member_id bigint,
    approved_at timestamp with time zone,
    reported_by_member_id bigint,
    reported_at timestamp with time zone,
    idempotency_key text NOT NULL,
    created_by bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    budget_override_reason text,
    budget_override_by_member_id bigint
);

CREATE TABLE IF NOT EXISTS finance.payment_allocations (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    bank_transaction_id bigint NOT NULL,
    request_id bigint NOT NULL,
    amount_minor numeric(38,0) NOT NULL,
    currency text NOT NULL,
    status text DEFAULT 'ACTIVE'::text NOT NULL,
    reversed_reason text,
    reversed_by_member_id bigint,
    reversed_at timestamp with time zone,
    idempotency_key text NOT NULL,
    created_by bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- =========================================================================
-- 2. CREATE INDEX (chỉ index của 20 bảng trên)
-- =========================================================================

CREATE INDEX IF NOT EXISTS idx_accounting_documents_ws_date ON finance.accounting_documents USING btree (workspace_id, document_date);
CREATE INDEX IF NOT EXISTS idx_accounting_documents_ws_status ON finance.accounting_documents USING btree (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_accounting_periods_posting_lookup ON finance.accounting_periods USING btree (workspace_id, status, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_accounting_periods_workspace_id ON finance.accounting_periods USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_accounting_regime_policies_ws_effective ON finance.accounting_regime_policies USING btree (workspace_id, effective_from);
CREATE INDEX IF NOT EXISTS idx_book_entries_entity ON finance.accounting_book_entries USING btree (legal_entity_id);
CREATE INDEX IF NOT EXISTS idx_book_entries_period ON finance.accounting_book_entries USING btree (period_id);
CREATE INDEX IF NOT EXISTS idx_cas_normalizer_log_conn ON finance.cas_normalizer_log USING btree (bank_connection_id, normalized_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cas_normalizer_log_dedup ON finance.cas_normalizer_log USING btree (bank_connection_id, provider_tx_id);
CREATE INDEX IF NOT EXISTS idx_coa_mappings_source ON finance.accounting_coa_mappings USING btree (source_regulation, source_account_code);
CREATE INDEX IF NOT EXISTS idx_coa_mappings_target ON finance.accounting_coa_mappings USING btree (target_regulation, target_account_code);
CREATE INDEX IF NOT EXISTS idx_finance_snapshots_workspace_as_of ON finance.finance_management_snapshots USING btree (workspace_id, as_of DESC);
CREATE INDEX IF NOT EXISTS idx_finance_snapshots_workspace_id ON finance.finance_management_snapshots USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_fiscal_profiles_workspace ON finance.accounting_fiscal_profiles USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_dlq_conn ON finance.ingestion_dlq USING btree (bank_connection_id, moved_at DESC);
CREATE INDEX IF NOT EXISTS idx_ingestion_events_status_received ON finance.ingestion_events USING btree (status, received_at);
CREATE INDEX IF NOT EXISTS idx_payment_allocations_bank_txn ON finance.payment_allocations USING btree (bank_transaction_id);
CREATE INDEX IF NOT EXISTS idx_payment_allocations_request ON finance.payment_allocations USING btree (request_id);
CREATE INDEX IF NOT EXISTS idx_payment_requests_workspace_entity ON finance.payment_requests USING btree (workspace_id, legal_entity_id);
CREATE INDEX IF NOT EXISTS idx_reconciliation_proposals_ws_status ON finance.document_reconciliation_proposals USING btree (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_regime_transition_workspace ON finance.accounting_regime_transition_logs USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_report_snapshots_period ON finance.accounting_report_snapshots USING btree (period_id, report_code);
CREATE UNIQUE INDEX IF NOT EXISTS uix_fiscal_profile_workspace_entity_year ON finance.accounting_fiscal_profiles USING btree (workspace_id, COALESCE(legal_entity_id, (0)::bigint), fiscal_year);
CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_requests_workspace_transfer_ref ON finance.payment_requests USING btree (workspace_id, transfer_reference) WHERE (transfer_reference IS NOT NULL);

-- =========================================================================
-- 3. ADD CONSTRAINT (PRIMARY KEY / UNIQUE / FOREIGN KEY) — bọc DO để idempotent
-- =========================================================================

-- ---- PRIMARY KEY ----
-- Bọc guard theo pg_constraint: thêm PK lần 2 raise `invalid_table_definition`
-- ("multiple primary keys ... not allowed") — KHÔNG phải `duplicate_object` —
-- nên chỉ EXCEPTION là chưa đủ idempotent khi re-apply thô.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'accounting_book_entries','accounting_coa_mappings','accounting_documents',
    'accounting_fiscal_profiles','accounting_mapping_confirmations','accounting_periods',
    'accounting_policies','accounting_profiles','accounting_regime_policies',
    'accounting_regime_transition_logs','accounting_report_mappings','accounting_report_snapshots',
    'cas_normalizer_log','document_reconciliation_proposals','finance_management_snapshots',
    'ingestion_dlq','ingestion_events','payment_allocations','payment_requests',
    'tax_obligation_instances'
  ] LOOP
    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conrelid = ('finance.' || t)::regclass AND contype = 'p'
    ) THEN
      EXECUTE format('ALTER TABLE finance.%I ADD CONSTRAINT %I PRIMARY KEY (id)', t, t || '_pkey');
    END IF;
  END LOOP;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;

-- ---- UNIQUE ----
DO $$ BEGIN ALTER TABLE finance.accounting_documents ADD CONSTRAINT accounting_documents_workspace_id_number_key UNIQUE (workspace_id, number); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.accounting_periods ADD CONSTRAINT accounting_periods_workspace_idempotency_key UNIQUE (workspace_id, idempotency_key); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.accounting_profiles ADD CONSTRAINT accounting_profiles_workspace_id_key UNIQUE (workspace_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.accounting_policies ADD CONSTRAINT uix_accounting_policy_entity UNIQUE (workspace_id, legal_entity_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.accounting_mapping_confirmations ADD CONSTRAINT uix_mapping_confirmation UNIQUE (workspace_id, regime_code, mapping_version); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.accounting_report_mappings ADD CONSTRAINT uix_report_mapping_line UNIQUE (regime_code, mapping_version, report_code, line_code); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.tax_obligation_instances ADD CONSTRAINT uix_tax_obligation UNIQUE (workspace_id, legal_entity_id, period_id, tax_name); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.payment_allocations ADD CONSTRAINT uq_payment_allocations_workspace_idempotency UNIQUE (workspace_id, idempotency_key); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.payment_requests ADD CONSTRAINT uq_payment_requests_workspace_idempotency UNIQUE (workspace_id, idempotency_key); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.ingestion_events ADD CONSTRAINT ingestion_events_bank_connection_id_provider_event_id_key UNIQUE (bank_connection_id, provider_event_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;

-- ---- FOREIGN KEY ----
-- Target trong bộ 20 bảng này hoặc trong `001` (bank_connections,
-- bank_transactions, cas_sync_inbox). 2 FK trỏ legal.regulation_versions bị bỏ
-- (xem header).
DO $$ BEGIN ALTER TABLE finance.accounting_book_entries ADD CONSTRAINT accounting_book_entries_document_id_fkey FOREIGN KEY (document_id) REFERENCES finance.accounting_documents(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.accounting_book_entries ADD CONSTRAINT accounting_book_entries_period_id_fkey FOREIGN KEY (period_id) REFERENCES finance.accounting_periods(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.accounting_documents ADD CONSTRAINT accounting_documents_regime_policy_id_fkey FOREIGN KEY (regime_policy_id) REFERENCES finance.accounting_regime_policies(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.accounting_periods ADD CONSTRAINT accounting_periods_fiscal_profile_id_fkey FOREIGN KEY (fiscal_profile_id) REFERENCES finance.accounting_fiscal_profiles(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.accounting_report_snapshots ADD CONSTRAINT accounting_report_snapshots_period_id_fkey FOREIGN KEY (period_id) REFERENCES finance.accounting_periods(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.cas_normalizer_log ADD CONSTRAINT cas_normalizer_log_bank_connection_id_fkey FOREIGN KEY (bank_connection_id) REFERENCES finance.bank_connections(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.cas_normalizer_log ADD CONSTRAINT cas_normalizer_log_bank_transaction_id_fkey FOREIGN KEY (bank_transaction_id) REFERENCES finance.bank_transactions(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.cas_normalizer_log ADD CONSTRAINT cas_normalizer_log_inbox_event_id_fkey FOREIGN KEY (inbox_event_id) REFERENCES finance.cas_sync_inbox(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.document_reconciliation_proposals ADD CONSTRAINT document_reconciliation_proposals_accounting_document_id_fkey FOREIGN KEY (accounting_document_id) REFERENCES finance.accounting_documents(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.document_reconciliation_proposals ADD CONSTRAINT document_reconciliation_proposals_bank_transaction_id_fkey FOREIGN KEY (bank_transaction_id) REFERENCES finance.bank_transactions(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.ingestion_dlq ADD CONSTRAINT ingestion_dlq_bank_connection_id_fkey FOREIGN KEY (bank_connection_id) REFERENCES finance.bank_connections(id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.ingestion_dlq ADD CONSTRAINT ingestion_dlq_inbox_event_id_fkey FOREIGN KEY (inbox_event_id) REFERENCES finance.cas_sync_inbox(id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.ingestion_events ADD CONSTRAINT ingestion_events_bank_connection_id_fkey FOREIGN KEY (bank_connection_id) REFERENCES finance.bank_connections(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.payment_allocations ADD CONSTRAINT payment_allocations_bank_transaction_id_fkey FOREIGN KEY (bank_transaction_id) REFERENCES finance.bank_transactions(id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.payment_allocations ADD CONSTRAINT payment_allocations_request_id_fkey FOREIGN KEY (request_id) REFERENCES finance.payment_requests(id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE finance.tax_obligation_instances ADD CONSTRAINT tax_obligation_instances_period_id_fkey FOREIGN KEY (period_id) REFERENCES finance.accounting_periods(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;


-- services/company/finance-legal/migrations/004_seed_ai_legal_applicability_corpus.up.sql
--
-- Baseline gap (Task 5F, epic 2026-09-10-baseline-completeness-harness-health):
-- squash R1 `001` giữ lại CẤU TRÚC `legal.regulation_sources` /
-- `legal.regulation_versions` / `legal.ai_applicability_rules` (đã khôi phục ở
-- `002_restore_baseline_gaps`), nhưng KHÔNG giữ lại NỘI DUNG corpus pháp lý mà
-- các migration tiền-squash 28 → 30 → 31 đã seed.
--
-- Hệ quả thật (fail-closed, không phải fail-open): `fetchActiveExecutableRules()`
-- trả mảng rỗng → `assessAiApplicability()` đi vào nhánh `rules.length === 0`
-- → luôn phát `PROFESSIONAL_REVIEW_REQUIRED` → `ai-compliance-snapshot.service.ts`
-- fail mọi `resolve-snapshot` với `LEGAL_REVIEW_PENDING`. Nghĩa là KHÔNG agent run
-- nào có thể tới model trên một DB baseline sạch.
--
-- Test buộc phải có migration này:
--   tests/e2e/test_ai_compliance_company_http.py::test_approved_run_reaches_company_then_model_once
--     (assert `RunStatus.COMPLETED`; trước seed này nhận `FAILED` kèm
--      "Deployment requires human legal review before runtime approval:
--       PROFESSIONAL_REVIEW_REQUIRED")
--
-- Nội dung dưới đây là TRẠNG THÁI CUỐI của corpus tiền-squash, chép nguyên văn
-- (không bịa thêm dữ liệu mới):
--   - `28_ai_compliance_legal_sources.up.sql` — 9 nguồn luật + version
--   - `30_ai_legal_source_corrections.up.sql` — SHA-256 THẬT của bản PDF công báo,
--     9 version "verified" (id 210-218, status ACTIVE) + 6 rule (id 301-306)
--   - `31_ai_legal_review_pending_correction.up.sql` — hạ 6 rule về
--     `review_status = 'PENDING_REVIEW'` và `legal_review_confirmed = false`,
--     vì migration 30 đã tự gán reviewer giả (`reviewer_member_id = 1`) mà không
--     có luật sư thật xác nhận. Trạng thái PENDING_REVIEW được giữ nguyên ở đây —
--     KHÔNG nâng lên 'REVIEWED' để test xanh; rule engine đọc đúng trạng thái này
--     và vẫn phát PROFESSIONAL_REVIEW_REQUIRED khi predicate khớp.
--   - Các row placeholder empty-hash id 110-117 (migration 28) mà migration 30 đã
--     đánh `INACTIVE_CORRECTION` thì KHÔNG seed lại — chúng chỉ là dấu vết sửa lỗi
--     của corpus cũ, không phải dữ liệu pháp lý.
--
-- Seed = dữ liệu, không phải cấu trúc → migration riêng, không gộp vào
-- `restore_baseline_gaps`. Expand-only + idempotent (upsert theo khoá tự nhiên).

-- ─── 1. Nguồn quy phạm pháp luật (content_hash = SHA-256 thật của PDF công báo) ───

INSERT INTO legal.regulation_sources (id, source_name, issuer, number, url, content_hash, layer, created_at, updated_at)
VALUES
  (10, 'Luật Trí tuệ nhân tạo', 'Quốc hội', '134/2025/QH15',
   'https://vanban.chinhphu.vn/?docid=216334&pageid=27160&typegroupid=3',
   '53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69', 'CURRENT_LAW', now(), now()),
  (11, 'Nghị định quy định chi tiết một số điều và biện pháp thi hành Luật Trí tuệ nhân tạo', 'Chính phủ', '142/2026/NĐ-CP',
   'https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/142-2026-ndcp.signed.pdf',
   '988fa7091b9f70615b8ae984e7e43b15293eb31398a113c86cc34f26666d5e40', 'CURRENT_LAW', now(), now()),
  (12, 'Quyết định ban hành Danh mục hệ thống trí tuệ nhân tạo có rủi ro cao', 'Thủ tướng Chính phủ', '33/2026/QĐ-TTg',
   'https://congbao.chinhphu.vn/van-ban/quyet-dinh-so-33-2026-qd-ttg-469951.htm',
   'f51e30980912a04ac347e34577779b42545285ad2df3c9f0cec5929b69a0e99b', 'CURRENT_LAW', now(), now()),
  (13, 'Luật Bảo vệ dữ liệu cá nhân', 'Quốc hội', '91/2025/QH15',
   'https://vanban.chinhphu.vn/?classid=1&docid=214590&pageid=27160&typegroup=',
   'c3b87f994cedcedb69d38c590dcca2bb7700aab65e518a2a3a5ffbf22048b9ee', 'CURRENT_LAW', now(), now()),
  (14, 'Thông tư ban hành Khung đạo đức trí tuệ nhân tạo quốc gia', 'Bộ Khoa học và Công nghệ', '05/2026/TT-BKHCN',
   'https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/3/05-bkhcn.pdf',
   '45616232b7023fef199cce2d52d5896d1db59b990a74fd40648b262d11490220', 'CURRENT_LAW', now(), now()),
  (15, 'Quyết định ban hành Danh mục bộ dữ liệu phục vụ phát triển trí tuệ nhân tạo trong các lĩnh vực thiết yếu', 'Thủ tướng Chính phủ', '804/QĐ-TTg',
   'https://vanban.chinhphu.vn/?pageid=27160&docid=208123',
   '38fe67ec952fe733a330939b9340a9d4ceb91877f00b6f8eea811d5c6399852c', 'POLICY_WATCH', now(), now()),
  (16, 'Quyết định ban hành Kế hoạch triển khai thi hành Luật Trí tuệ nhân tạo', 'Thủ tướng Chính phủ', '367/QĐ-TTg',
   'https://vanban.chinhphu.vn/?pageid=27160&docid=209456',
   '5cc8e35e58807295dae65fd46abc624334391b8bcf2fd35be9357256439c37af', 'POLICY_WATCH', now(), now()),
  (17, 'Quyết định phê duyệt Chương trình quốc gia phát triển nhân lực trí tuệ nhân tạo đến năm 2030, định hướng đến năm 2035', 'Thủ tướng Chính phủ', '1528/QĐ-TTg',
   'https://vanban.chinhphu.vn/?pageid=27160&docid=210789',
   '7f6e4800b8bc60d8b4a7a4e6882b25361c6cf78e13341463c8dc104084e3784f', 'POLICY_WATCH', now(), now()),
  (2,  'Nghị quyết ban hành Chiến lược quốc gia về khởi nghiệp sáng tạo', 'Chính phủ', '86/NQ-CP',
   'https://vanban.chinhphu.vn/?pageid=27160&docid=217558',
   '1e5208ca0a51c9ac7169c05a5186933a732204efd155f3ec66c1d8766b2bd476', 'POLICY_WATCH', now(), now())
ON CONFLICT (number) DO UPDATE SET
  source_name = EXCLUDED.source_name,
  issuer = EXCLUDED.issuer,
  url = EXCLUDED.url,
  content_hash = EXCLUDED.content_hash,
  layer = EXCLUDED.layer,
  updated_at = now();

-- ─── 2. Phiên bản đã xác minh document identity (SHA-256 + artifact ký số) ───
-- `legal_review_confirmed = false`: document identity là thật, nhưng CHƯA có
-- luật sư/founder xác nhận đã đọc và duyệt predicate (migration 31).

INSERT INTO legal.regulation_versions (
  id, regulation_source_id, version, effective_from, effective_to, superseded_by_id,
  status, content_hash, artifact_path, reviewer_member_id, reviewed_at,
  legal_review_confirmed, created_at
) VALUES
  (210, 10, '2026-verified', '2026-03-01', NULL, NULL, 'ACTIVE', '53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69', 'vb-ai/luat134.signed.pdf', NULL, NULL, false, now()),
  (211, 11, '2026-verified', '2026-05-01', NULL, NULL, 'ACTIVE', '988fa7091b9f70615b8ae984e7e43b15293eb31398a113c86cc34f26666d5e40', 'vb-ai/142-2026-ndcp.signed.pdf', NULL, NULL, false, now()),
  (212, 12, '2026-verified', '2026-08-15', NULL, NULL, 'ACTIVE', 'f51e30980912a04ac347e34577779b42545285ad2df3c9f0cec5929b69a0e99b', 'vb-ai/33-qdttg.signed.pdf', NULL, NULL, false, now()),
  (213, 13, '2025-verified', '2026-01-01', NULL, NULL, 'ACTIVE', 'c3b87f994cedcedb69d38c590dcca2bb7700aab65e518a2a3a5ffbf22048b9ee', 'vb-ai/91qh.signed.pdf', NULL, NULL, false, now()),
  (214, 14, '2026-verified', '2026-03-10', NULL, NULL, 'ACTIVE', '45616232b7023fef199cce2d52d5896d1db59b990a74fd40648b262d11490220', 'vb-ai/05-bkhcn.pdf', NULL, NULL, false, now()),
  (215, 15, '2026-verified', '2026-05-06', NULL, NULL, 'ACTIVE', '38fe67ec952fe733a330939b9340a9d4ceb91877f00b6f8eea811d5c6399852c', 'vb-ai/804-ttg.signed.pdf', NULL, NULL, false, now()),
  (216, 16, '2026-verified', '2026-02-28', NULL, NULL, 'ACTIVE', '5cc8e35e58807295dae65fd46abc624334391b8bcf2fd35be9357256439c37af', 'vb-ai/367-ttg.signed.pdf', NULL, NULL, false, now()),
  (217, 17, '2026-verified', '2026-08-11', NULL, NULL, 'ACTIVE', '7f6e4800b8bc60d8b4a7a4e6882b25361c6cf78e13341463c8dc104084e3784f', 'vb-ai/1528_qd-ttg_11082026-signed.signed.pdf', NULL, NULL, false, now()),
  (218, 2,  '2026-verified', '2026-04-05', NULL, NULL, 'ACTIVE', '1e5208ca0a51c9ac7169c05a5186933a732204efd155f3ec66c1d8766b2bd476', 'vb-ai/86-nqcp.signed.pdf', NULL, NULL, false, now())
ON CONFLICT (regulation_source_id, version) DO UPDATE SET
  effective_from = EXCLUDED.effective_from,
  status = EXCLUDED.status,
  content_hash = EXCLUDED.content_hash,
  artifact_path = EXCLUDED.artifact_path,
  legal_review_confirmed = EXCLUDED.legal_review_confirmed;

-- ─── 3. Quy tắc áp dụng AI (review_status = 'PENDING_REVIEW' theo migration 31) ───

INSERT INTO legal.ai_applicability_rules (
  id, rule_id, rule_version, regulation_source_id, regulation_version_id, source_content_hash,
  effective_from, effective_to, review_status, layer, effect, reason_code, description,
  predicate, mandatory_evidence_type, created_at, updated_at
) VALUES
  (301, 'STATUTORY_MODE_ADVISORY', '1.0.0', 10, 210,
   '53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69',
   '2026-03-01', NULL, 'PENDING_REVIEW', 'CURRENT_LAW', 'BLOCK', 'NON_ADVISORY_MODE',
   'COSA chỉ cho phép triển khai chế độ ADVISORY_ONLY phục vụ doanh nghiệp tư nhân theo Luật AI 134/2025/QH15',
   '{"deploymentModeNotEquals": "ADVISORY_ONLY"}'::jsonb, 'LEGAL_ASSESSMENT', now(), now()),
  (302, 'STATUTORY_PROHIBITED_DOMAINS', '1.0.0', 12, 212,
   'f51e30980912a04ac347e34577779b42545285ad2df3c9f0cec5929b69a0e99b',
   '2026-08-15', NULL, 'PENDING_REVIEW', 'CURRENT_LAW', 'BLOCK', 'PROHIBITED_DECISION_DOMAIN',
   'Cấm quyết định tự động không có con người giám sát trong các lĩnh vực có rủi ro cao theo Quyết định 33/2026/QĐ-TTg',
   '{"isProhibitedDomain": true}'::jsonb, 'HIGH_RISK_CONFORMITY_CERTIFICATE', now(), now()),
  (303, 'STATUTORY_PROVIDER_APPROVED', '1.0.0', 14, 214,
   '45616232b7023fef199cce2d52d5896d1db59b990a74fd40648b262d11490220',
   '2026-03-10', NULL, 'PENDING_REVIEW', 'CURRENT_LAW', 'BLOCK', 'PROVIDER_NOT_APPROVED',
   'Nhà cung cấp mô hình phải có hồ sơ APPROVED tuân thủ Khung đạo đức AI quốc gia theo Thông tư 05/2026/TT-BKHCN',
   '{"providerProfileStatusNotEquals": "APPROVED"}'::jsonb, 'PROVIDER_COMPLIANCE_REVIEW', now(), now()),
  (304, 'STATUTORY_LEGAL_PROFESSIONAL_REVIEW', '1.0.0', 10, 210,
   '53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69',
   '2026-03-01', NULL, 'PENDING_REVIEW', 'PROFESSIONAL_REVIEW', 'REVIEW', 'PROFESSIONAL_LEGAL_REVIEW_REQUIRED',
   'Nghiệp vụ tư vấn pháp lý có tranh chấp, tố tụng cần luật sư/chuyên gia rà soát',
   '{"decisionDomain": "LEGAL", "purposeKeywords": ["litigation", "dispute", "tranh chấp", "khởi kiện", "tố tụng"]}'::jsonb, NULL, now(), now()),
  (305, 'POLICY_WATCH_QD804', '1.0.0', 15, 215,
   '38fe67ec952fe733a330939b9340a9d4ceb91877f00b6f8eea811d5c6399852c',
   '2026-05-06', NULL, 'PENDING_REVIEW', 'POLICY_WATCH', 'NOTICE', 'POLICY_WATCH_AI_DATA_CATALOG_804',
   'Theo dõi Danh mục bộ dữ liệu phục vụ phát triển AI thiết yếu theo Quyết định 804/QĐ-TTg',
   '{"alwaysNotice": true}'::jsonb, NULL, now(), now()),
  (306, 'POLICY_WATCH_QD1528', '1.0.0', 17, 217,
   '7f6e4800b8bc60d8b4a7a4e6882b25361c6cf78e13341463c8dc104084e3784f',
   '2026-08-11', NULL, 'PENDING_REVIEW', 'POLICY_WATCH', 'NOTICE', 'POLICY_WATCH_AI_HUMAN_RESOURCES_1528',
   'Theo dõi Chương trình quốc gia phát triển nhân lực AI theo Quyết định 1528/QĐ-TTg',
   '{"alwaysNotice": true}'::jsonb, NULL, now(), now())
ON CONFLICT (rule_id) DO UPDATE SET
  regulation_source_id = EXCLUDED.regulation_source_id,
  regulation_version_id = EXCLUDED.regulation_version_id,
  source_content_hash = EXCLUDED.source_content_hash,
  effective_from = EXCLUDED.effective_from,
  review_status = EXCLUDED.review_status,
  layer = EXCLUDED.layer,
  effect = EXCLUDED.effect,
  reason_code = EXCLUDED.reason_code,
  description = EXCLUDED.description,
  predicate = EXCLUDED.predicate,
  mandatory_evidence_type = EXCLUDED.mandatory_evidence_type,
  updated_at = now();
