-- GENERATED from a pg_dump --schema-only of the fully-migrated dev DB,
-- then filtered to the Founder Trial R1 retained allowlist. Review before use.
-- Task 10 of docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md

CREATE SCHEMA IF NOT EXISTS operating;
CREATE SCHEMA IF NOT EXISTS strategy;

CREATE TABLE IF NOT EXISTS strategy.projects (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    lifecycle_stage character varying(50) DEFAULT 'P0_DISCOVERY'::character varying NOT NULL,
    current_gate character varying(50),
    status character varying(50) DEFAULT 'ACTIVE'::character varying NOT NULL,
    owner_member_id bigint,
    project_type character varying(50),
    strategic_priority character varying(50),
    founder_attention_budget double precision,
    portfolio_id bigint,
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    stage_version integer DEFAULT 0 NOT NULL,
    stage_entered_at timestamp with time zone,
    CONSTRAINT projects_lifecycle_stage_chk CHECK (((lifecycle_stage)::text = ANY ((ARRAY['P0_DISCOVERY'::character varying, 'P1_PROBLEM_VALIDATION'::character varying, 'P2_SOLUTION_VALIDATION'::character varying, 'P3_BUILD_VALIDATE'::character varying, 'P4_GO_TO_MARKET'::character varying, 'P5_OPERATE_GROWTH'::character varying, 'P6_SCALE_GOVERN'::character varying])::text[]))),
    CONSTRAINT projects_status_chk CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'PAUSED'::character varying, 'COMPLETED'::character varying, 'ARCHIVED'::character varying])::text[])))
);

DO $$ BEGIN
  ALTER TABLE ONLY strategy.projects ADD CONSTRAINT projects_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY strategy.projects ADD CONSTRAINT uix_projects_id_workspace UNIQUE (id, workspace_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_projects_portfolio ON strategy.projects USING btree (portfolio_id);

CREATE INDEX IF NOT EXISTS idx_projects_workspace ON strategy.projects USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS operating.twelve_week_cycles (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint,
    theme character varying(255),
    vision_statement text DEFAULT ''::text NOT NULL,
    stage_at_start character varying(50) DEFAULT 'S1_PROBLEM_VALIDATION'::character varying NOT NULL,
    current_week integer DEFAULT 1 NOT NULL,
    duration_weeks integer DEFAULT 12 NOT NULL,
    overall_execution_score double precision DEFAULT 0.0 NOT NULL,
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    commitment_level character varying(50),
    status character varying(50) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    display_name character varying(255),
    timezone character varying(100) DEFAULT 'UTC'::character varying NOT NULL,
    start_local_date date,
    end_local_date_exclusive date,
    revision integer DEFAULT 1 NOT NULL,
    calendar_state character varying(50) DEFAULT 'READY'::character varying NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY operating.twelve_week_cycles ADD CONSTRAINT twelve_week_cycles_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.twelve_week_cycles ADD CONSTRAINT fk_twelve_week_cycles_project_id FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_twelve_week_cycles_workspace ON operating.twelve_week_cycles USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS strategy.decision_records (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint,
    gate_evaluation_id bigint,
    decision character varying(50) NOT NULL,
    actor_member_id bigint,
    evidence_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    decision_type text,
    created_by_kind text,
    created_by_ref text,
    evidence_refs jsonb DEFAULT '[]'::jsonb,
    regulation_refs jsonb DEFAULT '[]'::jsonb,
    confidence numeric,
    assumptions jsonb DEFAULT '[]'::jsonb,
    alternatives jsonb DEFAULT '[]'::jsonb,
    policy_version text,
    ai_prompt_version text,
    founder_decision text,
    decided_at timestamp with time zone,
    CONSTRAINT decision_records_created_by_kind_check CHECK ((created_by_kind = ANY (ARRAY['FOUNDER'::text, 'AI'::text, 'SYSTEM'::text]))),
    CONSTRAINT decision_records_founder_decision_check CHECK ((founder_decision = ANY (ARRAY['accepted'::text, 'rejected'::text, 'deferred'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY strategy.decision_records ADD CONSTRAINT decision_records_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY strategy.decision_records ADD CONSTRAINT decision_records_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_decision_records_project ON strategy.decision_records USING btree (project_id);

CREATE INDEX IF NOT EXISTS idx_decision_records_workspace_type_created ON strategy.decision_records USING btree (workspace_id, decision_type, created_at);


CREATE TABLE IF NOT EXISTS operating.cycle_reviews (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint,
    cycle_id bigint NOT NULL,
    kind character varying(50) NOT NULL,
    scheduled_week_no integer NOT NULL,
    scheduled_at timestamp with time zone,
    status character varying(50) DEFAULT 'SCHEDULED'::character varying NOT NULL,
    kr_snapshots jsonb DEFAULT '[]'::jsonb NOT NULL,
    initiative_snapshots jsonb DEFAULT '[]'::jsonb NOT NULL,
    pestel_snapshots jsonb DEFAULT '[]'::jsonb NOT NULL,
    decision_id bigint,
    conclusion text,
    conducted_by_member_id bigint,
    conducted_at timestamp with time zone,
    settings_revision integer,
    revision integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

DO $$ BEGIN
  ALTER TABLE ONLY operating.cycle_reviews ADD CONSTRAINT cycle_reviews_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.cycle_reviews ADD CONSTRAINT cycle_reviews_cycle_id_fkey FOREIGN KEY (cycle_id) REFERENCES operating.twelve_week_cycles(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.cycle_reviews ADD CONSTRAINT cycle_reviews_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES strategy.decision_records(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.cycle_reviews ADD CONSTRAINT cycle_reviews_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS ix_cycle_reviews_workspace_cycle ON operating.cycle_reviews USING btree (workspace_id, cycle_id, scheduled_week_no, kind) WHERE (deleted_at IS NULL);

CREATE UNIQUE INDEX IF NOT EXISTS uix_cycle_reviews_active_slot ON operating.cycle_reviews USING btree (cycle_id, kind, scheduled_week_no) WHERE (((status)::text <> ALL ((ARRAY['SUPERSEDED'::character varying, 'SKIPPED'::character varying])::text[])) AND (deleted_at IS NULL));


CREATE TABLE IF NOT EXISTS operating.cycle_revisions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    cycle_id bigint NOT NULL,
    revision integer NOT NULL,
    before_state jsonb NOT NULL,
    after_state jsonb NOT NULL,
    reason text,
    actor_id text,
    actor_kind text DEFAULT 'user'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY operating.cycle_revisions ADD CONSTRAINT cycle_revisions_cycle_id_revision_key UNIQUE (cycle_id, revision);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.cycle_revisions ADD CONSTRAINT cycle_revisions_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.cycle_revisions ADD CONSTRAINT cycle_revisions_cycle_id_fkey FOREIGN KEY (cycle_id) REFERENCES operating.twelve_week_cycles(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_cycle_revisions_ws_cycle ON operating.cycle_revisions USING btree (workspace_id, cycle_id, revision DESC);


CREATE TABLE IF NOT EXISTS operating.weekly_plans (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    cycle_id bigint NOT NULL,
    week_no integer NOT NULL,
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    focus text,
    mission text,
    execution_score double precision,
    outcome_score double precision,
    reflection text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    decision_id bigint
);

DO $$ BEGIN
  ALTER TABLE ONLY operating.weekly_plans ADD CONSTRAINT uix_weekly_plan_cycle_week UNIQUE (cycle_id, week_no);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.weekly_plans ADD CONSTRAINT weekly_plans_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.weekly_plans ADD CONSTRAINT weekly_plans_cycle_id_fkey FOREIGN KEY (cycle_id) REFERENCES operating.twelve_week_cycles(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.weekly_plans ADD CONSTRAINT weekly_plans_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES strategy.decision_records(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_weekly_plans_cycle ON operating.weekly_plans USING btree (cycle_id);

CREATE INDEX IF NOT EXISTS idx_weekly_plans_workspace ON operating.weekly_plans USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS operating.weekly_commitments (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    weekly_plan_id bigint NOT NULL,
    initiative_id bigint,
    title character varying(255) NOT NULL,
    status character varying(50) DEFAULT 'todo'::character varying NOT NULL,
    planned_effort character varying(50),
    commitment_owner_type character varying(50) DEFAULT 'FOUNDER'::character varying,
    execution_mode character varying(50) DEFAULT 'MANUAL'::character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    source_action_id character varying(255),
    source_revision integer DEFAULT 1 NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    owner_member_id bigint,
    purpose_type character varying(50) DEFAULT 'KR'::character varying NOT NULL,
    purpose_ref text,
    done_criteria jsonb,
    committed_at timestamp with time zone,
    decision_id bigint
);

DO $$ BEGIN
  ALTER TABLE ONLY operating.weekly_commitments ADD CONSTRAINT weekly_commitments_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.weekly_commitments ADD CONSTRAINT weekly_commitments_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES strategy.decision_records(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.weekly_commitments ADD CONSTRAINT weekly_commitments_weekly_plan_id_fkey FOREIGN KEY (weekly_plan_id) REFERENCES operating.weekly_plans(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_weekly_commitments_plan ON operating.weekly_commitments USING btree (weekly_plan_id);

CREATE INDEX IF NOT EXISTS idx_weekly_commitments_workspace ON operating.weekly_commitments USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS operating.tasks (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    title text NOT NULL,
    idempotency_key text,
    status text DEFAULT 'todo'::text NOT NULL,
    priority text DEFAULT 'medium'::text NOT NULL,
    planned_start_at timestamp with time zone,
    due_at timestamp with time zone,
    timezone text DEFAULT 'UTC'::text NOT NULL,
    source text,
    completion_policy text,
    initiative_id bigint,
    weekly_commitment_id bigint,
    sort_key double precision,
    assignee_member_id bigint,
    owner_member_id bigint,
    execution_mode text,
    function text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    source_action_id character varying(255),
    source_revision integer DEFAULT 1 NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    active_outcome_contract_id bigint
);

DO $$ BEGIN
  ALTER TABLE ONLY operating.tasks ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.tasks ADD CONSTRAINT tasks_workspace_id_idempotency_key_key UNIQUE (workspace_id, idempotency_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.tasks ADD CONSTRAINT uix_tasks_id_workspace UNIQUE (id, workspace_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY operating.tasks ADD CONSTRAINT fk_tasks_weekly_commitment_id FOREIGN KEY (weekly_commitment_id) REFERENCES operating.weekly_commitments(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_tasks_function ON operating.tasks USING btree (function);

CREATE INDEX IF NOT EXISTS idx_tasks_workspace_id ON operating.tasks USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS strategy.assumptions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    statement text NOT NULL,
    importance integer DEFAULT 1 NOT NULL,
    uncertainty integer DEFAULT 1 NOT NULL,
    risk_score double precision DEFAULT 1.0 NOT NULL,
    status character varying(50) DEFAULT 'untested'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

DO $$ BEGIN
  ALTER TABLE ONLY strategy.assumptions ADD CONSTRAINT assumptions_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY strategy.assumptions ADD CONSTRAINT assumptions_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_assumptions_project ON strategy.assumptions USING btree (project_id);


CREATE TABLE IF NOT EXISTS strategy.evidence_ingestions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    source_system character varying(50) NOT NULL,
    source_record_id text NOT NULL,
    source_payload_hash text NOT NULL,
    artifact_ref text,
    source_url text,
    observed_at timestamp with time zone NOT NULL,
    ingested_by_member_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT evidence_ingestions_source_system_chk CHECK (((source_system)::text = ANY ((ARRAY['interview'::character varying, 'crm'::character varying, 'telemetry'::character varying, 'payment'::character varying])::text[])))
);

DO $$ BEGIN
  ALTER TABLE ONLY strategy.evidence_ingestions ADD CONSTRAINT evidence_ingestions_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_evidence_ingestions_ws_proj ON strategy.evidence_ingestions USING btree (workspace_id, project_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_evidence_ingestions_source_hash ON strategy.evidence_ingestions USING btree (workspace_id, source_system, source_record_id, source_payload_hash);


CREATE TABLE IF NOT EXISTS strategy.experiments (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    assumption_id bigint,
    hypothesis text NOT NULL,
    method text NOT NULL,
    success_criteria text NOT NULL,
    budget double precision DEFAULT 0.0 NOT NULL,
    owner_member_id bigint,
    status character varying(50) DEFAULT 'draft'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

DO $$ BEGIN
  ALTER TABLE ONLY strategy.experiments ADD CONSTRAINT experiments_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY strategy.experiments ADD CONSTRAINT experiments_assumption_id_fkey FOREIGN KEY (assumption_id) REFERENCES strategy.assumptions(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY strategy.experiments ADD CONSTRAINT experiments_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_experiments_assumption ON strategy.experiments USING btree (assumption_id);

CREATE INDEX IF NOT EXISTS idx_experiments_project ON strategy.experiments USING btree (project_id);


CREATE TABLE IF NOT EXISTS strategy.evidence (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    experiment_id bigint,
    project_id bigint NOT NULL,
    source_type character varying(50) NOT NULL,
    claim text NOT NULL,
    strength double precision DEFAULT 0.0 NOT NULL,
    confidence double precision DEFAULT 0.0 NOT NULL,
    supports_or_refutes character varying(20) DEFAULT 'supports'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    status character varying(30) DEFAULT 'candidate'::character varying NOT NULL,
    review_comment text,
    reviewed_by_member_id bigint,
    reviewed_at timestamp with time zone,
    evidence_ingestion_id bigint,
    artifact_ref text,
    source_url text,
    source_system character varying(50),
    fact_or_inference character varying(30) DEFAULT 'inference'::character varying NOT NULL,
    observed_at timestamp with time zone,
    fresh_until timestamp with time zone
);

DO $$ BEGIN
  ALTER TABLE ONLY strategy.evidence ADD CONSTRAINT evidence_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY strategy.evidence ADD CONSTRAINT evidence_evidence_ingestion_id_fkey FOREIGN KEY (evidence_ingestion_id) REFERENCES strategy.evidence_ingestions(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY strategy.evidence ADD CONSTRAINT evidence_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES strategy.experiments(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY strategy.evidence ADD CONSTRAINT evidence_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_evidence_experiment ON strategy.evidence USING btree (experiment_id);

CREATE INDEX IF NOT EXISTS idx_evidence_project ON strategy.evidence USING btree (project_id);

CREATE INDEX IF NOT EXISTS idx_evidence_ws_proj_status ON strategy.evidence USING btree (workspace_id, project_id, status);


CREATE TABLE IF NOT EXISTS strategy.interviews (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    contact_ref bigint,
    notes text NOT NULL,
    conducted_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

DO $$ BEGIN
  ALTER TABLE ONLY strategy.interviews ADD CONSTRAINT interviews_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY strategy.interviews ADD CONSTRAINT interviews_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_interviews_project ON strategy.interviews USING btree (project_id);


CREATE TABLE IF NOT EXISTS strategy.project_operating_setups (
    project_id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    status text DEFAULT 'NOT_STARTED'::text NOT NULL,
    target_customer text,
    problem_statement text,
    evidence_level text,
    recommended_stage text,
    selected_stage text,
    stage_duration_weeks integer,
    stage_target_date timestamp with time zone,
    weekly_review_weekday smallint,
    weekly_review_time text,
    first_week_outcome text,
    first_week_actions jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    round_start_date timestamp with time zone,
    ai_suggestion_status text,
    ai_suggestion_run_id text,
    ai_suggested_outcome text,
    ai_suggested_actions jsonb,
    ai_suggestion_requested_at timestamp with time zone,
    cycle_duration_weeks integer,
    CONSTRAINT project_operating_setups_ai_suggestion_status_check CHECK ((ai_suggestion_status = ANY (ARRAY['dispatched'::text, 'completed'::text, 'failed'::text]))),
    CONSTRAINT project_operating_setups_evidence_level_check CHECK ((evidence_level = ANY (ARRAY['NONE'::text, 'ONE_TO_FOUR_INTERVIEWS'::text, 'FIVE_PLUS_INTERVIEWS'::text, 'PROTOTYPE_OR_REVENUE'::text]))),
    CONSTRAINT project_operating_setups_recommended_stage_check CHECK ((recommended_stage = ANY (ARRAY['P0_DISCOVERY'::text, 'P1_PROBLEM_VALIDATION'::text]))),
    CONSTRAINT project_operating_setups_selected_stage_check CHECK ((selected_stage = ANY (ARRAY['P0_DISCOVERY'::text, 'P1_PROBLEM_VALIDATION'::text]))),
    CONSTRAINT project_operating_setups_stage_duration_weeks_check CHECK (((stage_duration_weeks >= 1) AND (stage_duration_weeks <= 4))),
    CONSTRAINT project_operating_setups_status_check CHECK ((status = ANY (ARRAY['NOT_STARTED'::text, 'IN_PROGRESS'::text, 'ACTIVE'::text]))),
    CONSTRAINT project_operating_setups_weekly_review_time_check CHECK ((weekly_review_time ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'::text)),
    CONSTRAINT project_operating_setups_weekly_review_weekday_check CHECK (((weekly_review_weekday >= 1) AND (weekly_review_weekday <= 7)))
);

DO $$ BEGIN
  ALTER TABLE ONLY strategy.project_operating_setups ADD CONSTRAINT project_operating_setups_pkey PRIMARY KEY (project_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY strategy.project_operating_setups ADD CONSTRAINT project_operating_setups_project_id_workspace_id_fkey FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_project_operating_setups_workspace_status ON strategy.project_operating_setups USING btree (workspace_id, status, updated_at DESC);


CREATE TABLE IF NOT EXISTS strategy.workspace_strategy_settings (
    workspace_id bigint NOT NULL,
    strategy_method text DEFAULT 'CLASSIC'::text NOT NULL,
    bsc_mode text DEFAULT 'OFF'::text NOT NULL,
    enabled_bsc_perspectives jsonb DEFAULT '[]'::jsonb NOT NULL,
    tows_selection_limit smallint DEFAULT 1 NOT NULL,
    weekly_review_enabled boolean DEFAULT true NOT NULL,
    mid_cycle_review_policy text DEFAULT 'AUTO'::text NOT NULL,
    end_cycle_review_enabled boolean DEFAULT true NOT NULL,
    allowed_agent_profiles jsonb DEFAULT '[]'::jsonb NOT NULL,
    approval_policy text DEFAULT 'FOUNDER_ONLY'::text NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    updated_by_member_id bigint,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT workspace_strategy_settings_approval_policy_check CHECK ((approval_policy = ANY (ARRAY['FOUNDER_ONLY'::text, 'DELEGATED_APPROVER'::text]))),
    CONSTRAINT workspace_strategy_settings_bsc_mode_check CHECK ((bsc_mode = ANY (ARRAY['OFF'::text, 'OPTIONAL'::text, 'REQUIRED'::text]))),
    CONSTRAINT workspace_strategy_settings_mid_cycle_review_policy_check CHECK ((mid_cycle_review_policy = ANY (ARRAY['OFF'::text, 'AUTO'::text, 'CUSTOM'::text]))),
    CONSTRAINT workspace_strategy_settings_strategy_method_check CHECK ((strategy_method = ANY (ARRAY['CLASSIC'::text, 'BSC_FILTER'::text]))),
    CONSTRAINT workspace_strategy_settings_tows_selection_limit_check CHECK (((tows_selection_limit >= 1) AND (tows_selection_limit <= 2)))
);

DO $$ BEGIN
  ALTER TABLE ONLY strategy.workspace_strategy_settings ADD CONSTRAINT workspace_strategy_settings_pkey PRIMARY KEY (workspace_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY strategy.workspace_strategy_settings ADD CONSTRAINT workspace_strategy_settings_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

