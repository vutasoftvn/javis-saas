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
