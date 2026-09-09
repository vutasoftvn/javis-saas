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

