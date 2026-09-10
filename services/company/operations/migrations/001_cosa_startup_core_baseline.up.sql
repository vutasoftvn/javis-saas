-- COSA Startup Core baseline migration for services/company/operations
-- Canonical Execution Hierarchy:
-- Workspace -> Project -> OKR (Objective -> Key Result) -> Initiative -> Operating Cycle (1..12 weeks) -> Week -> Commitment -> Task

CREATE SCHEMA IF NOT EXISTS operating;
CREATE SCHEMA IF NOT EXISTS strategy;

-- 1. strategy.projects
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
    CONSTRAINT projects_pkey PRIMARY KEY (id),
    CONSTRAINT uix_projects_id_workspace UNIQUE (id, workspace_id),
    CONSTRAINT projects_lifecycle_stage_chk CHECK (((lifecycle_stage)::text = ANY ((ARRAY['P0_DISCOVERY'::character varying, 'P1_PROBLEM_VALIDATION'::character varying, 'P2_SOLUTION_VALIDATION'::character varying, 'P3_BUILD_VALIDATE'::character varying, 'P4_GO_TO_MARKET'::character varying, 'P5_OPERATE_GROWTH'::character varying, 'P6_SCALE_GOVERN'::character varying])::text[]))),
    CONSTRAINT projects_status_chk CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'PAUSED'::character varying, 'COMPLETED'::character varying, 'ARCHIVED'::character varying])::text[])))
);
CREATE INDEX IF NOT EXISTS idx_projects_workspace ON strategy.projects USING btree (workspace_id);

-- 2. strategy.okr_objectives
CREATE TABLE IF NOT EXISTS strategy.okr_objectives (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    title text NOT NULL,
    why text,
    owner_member_id bigint,
    status text DEFAULT 'draft'::text NOT NULL,
    published_by_member_id bigint,
    published_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT okr_objectives_pkey PRIMARY KEY (id),
    CONSTRAINT uix_okr_objectives_id_workspace UNIQUE (id, workspace_id),
    CONSTRAINT fk_okr_objective_project_ws FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects (id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_okr_objectives_project ON strategy.okr_objectives USING btree (workspace_id, project_id);

-- 3. strategy.key_results
CREATE TABLE IF NOT EXISTS strategy.key_results (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    objective_id bigint NOT NULL,
    title text,
    metric_id bigint,
    baseline_value double precision,
    current_value double precision,
    target_value double precision,
    unit text,
    cadence text,
    metric_type text,
    scoring_type character varying(50) DEFAULT 'LINEAR_INCREASE'::character varying NOT NULL,
    metric_contract_version integer,
    evidence_refs jsonb DEFAULT '[]'::jsonb,
    status text DEFAULT 'draft'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT key_results_pkey PRIMARY KEY (id),
    CONSTRAINT uix_key_results_id_workspace UNIQUE (id, workspace_id),
    CONSTRAINT fk_key_result_objective_ws FOREIGN KEY (objective_id, workspace_id) REFERENCES strategy.okr_objectives (id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_key_results_objective ON strategy.key_results USING btree (workspace_id, objective_id);

-- 4. strategy.initiatives
CREATE TABLE IF NOT EXISTS strategy.initiatives (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    key_result_id bigint NOT NULL,
    title text NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    owner_member_id bigint,
    description text,
    intended_outcome text,
    start_date timestamp with time zone,
    target_date timestamp with time zone,
    milestones jsonb DEFAULT '[]'::jsonb NOT NULL,
    approval_status text DEFAULT 'DRAFT'::text NOT NULL,
    approved_by_member_id bigint,
    approved_at timestamp with time zone,
    decision_id bigint,
    settings_revision integer,
    revision integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT initiatives_pkey PRIMARY KEY (id),
    CONSTRAINT uix_initiatives_id_workspace UNIQUE (id, workspace_id),
    CONSTRAINT initiatives_approval_status_check CHECK ((approval_status = ANY (ARRAY['DRAFT'::text, 'PENDING_APPROVAL'::text, 'APPROVED'::text, 'REJECTED'::text, 'CLOSED'::text]))),
    CONSTRAINT fk_initiative_project_ws FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects (id, workspace_id) ON DELETE CASCADE,
    CONSTRAINT fk_initiative_key_result_ws FOREIGN KEY (key_result_id, workspace_id) REFERENCES strategy.key_results (id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_initiatives_project ON strategy.initiatives USING btree (workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_initiatives_key_result ON strategy.initiatives USING btree (workspace_id, key_result_id);

-- 5. operating.twelve_week_cycles
CREATE TABLE IF NOT EXISTS operating.twelve_week_cycles (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    duration_weeks integer DEFAULT 12 NOT NULL,
    current_week integer DEFAULT 1 NOT NULL,
    theme character varying(255),
    vision_statement text DEFAULT ''::text NOT NULL,
    stage_at_start character varying(50) DEFAULT 'S1_PROBLEM_VALIDATION'::character varying NOT NULL,
    overall_execution_score double precision DEFAULT 0.0 NOT NULL,
    display_name character varying(255),
    timezone character varying(100) DEFAULT 'UTC'::character varying NOT NULL,
    start_local_date date,
    end_local_date_exclusive date,
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    commitment_level character varying(50),
    status character varying(50) DEFAULT 'ACTIVE'::character varying NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    calendar_state character varying(50) DEFAULT 'READY'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT twelve_week_cycles_pkey PRIMARY KEY (id),
    CONSTRAINT uix_twelve_week_cycles_id_workspace UNIQUE (id, workspace_id),
    CONSTRAINT ck_cycle_duration CHECK (duration_weeks BETWEEN 1 AND 12),
    CONSTRAINT fk_cycle_project_ws FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects (id, workspace_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS uix_active_cycle_per_project ON operating.twelve_week_cycles (workspace_id, project_id) WHERE status = 'ACTIVE' AND deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_twelve_week_cycles_workspace ON operating.twelve_week_cycles USING btree (workspace_id, project_id);

-- 6. operating.weekly_plans
CREATE TABLE IF NOT EXISTS operating.weekly_plans (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    cycle_id bigint NOT NULL,
    week_no integer NOT NULL,
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    focus text,
    mission text,
    execution_score double precision,
    outcome_score double precision,
    reflection text,
    decision_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT weekly_plans_pkey PRIMARY KEY (id),
    CONSTRAINT uix_weekly_plans_id_workspace UNIQUE (id, workspace_id),
    CONSTRAINT fk_weekly_plan_cycle_ws FOREIGN KEY (cycle_id, workspace_id) REFERENCES operating.twelve_week_cycles (id, workspace_id) ON DELETE CASCADE,
    CONSTRAINT fk_weekly_plan_project_ws FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects (id, workspace_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS uix_weekly_plans_cycle_week ON operating.weekly_plans (workspace_id, project_id, cycle_id, week_no) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_weekly_plans_cycle ON operating.weekly_plans USING btree (cycle_id);
CREATE INDEX IF NOT EXISTS idx_weekly_plans_workspace ON operating.weekly_plans USING btree (workspace_id);

-- 7. operating.weekly_commitments
CREATE TABLE IF NOT EXISTS operating.weekly_commitments (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    weekly_plan_id bigint NOT NULL,
    initiative_id bigint,
    title character varying(255) NOT NULL,
    status character varying(50) DEFAULT 'todo'::character varying NOT NULL,
    planned_effort character varying(50),
    commitment_owner_type character varying(50) DEFAULT 'FOUNDER'::character varying,
    execution_mode character varying(50) DEFAULT 'MANUAL'::character varying,
    source_action_id character varying(255),
    source_revision integer DEFAULT 1 NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    owner_member_id bigint,
    purpose_type character varying(50) DEFAULT 'KR'::character varying NOT NULL,
    purpose_ref text,
    done_criteria jsonb,
    committed_at timestamp with time zone,
    decision_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT weekly_commitments_pkey PRIMARY KEY (id),
    CONSTRAINT uix_weekly_commitments_id_workspace UNIQUE (id, workspace_id),
    CONSTRAINT fk_weekly_commitment_plan_ws FOREIGN KEY (weekly_plan_id, workspace_id) REFERENCES operating.weekly_plans (id, workspace_id) ON DELETE CASCADE,
    CONSTRAINT fk_weekly_commitment_project_ws FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects (id, workspace_id) ON DELETE CASCADE,
    CONSTRAINT fk_weekly_commitment_initiative_ws FOREIGN KEY (initiative_id, workspace_id) REFERENCES strategy.initiatives (id, workspace_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_weekly_commitments_plan ON operating.weekly_commitments USING btree (weekly_plan_id);
CREATE INDEX IF NOT EXISTS idx_weekly_commitments_workspace ON operating.weekly_commitments USING btree (workspace_id, project_id);

-- 8. operating.tasks
CREATE TABLE IF NOT EXISTS operating.tasks (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    weekly_commitment_id bigint,
    initiative_id bigint,
    title text NOT NULL,
    idempotency_key text,
    status text DEFAULT 'todo'::text NOT NULL,
    priority text DEFAULT 'medium'::text NOT NULL,
    planned_start_at timestamp with time zone,
    due_at timestamp with time zone,
    timezone text DEFAULT 'UTC'::text NOT NULL,
    source text,
    completion_policy text,
    sort_key double precision,
    assignee_member_id bigint,
    owner_member_id bigint,
    execution_mode text,
    function text,
    source_action_id character varying(255),
    source_revision integer DEFAULT 1 NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    active_outcome_contract_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT tasks_pkey PRIMARY KEY (id),
    CONSTRAINT uix_tasks_id_workspace UNIQUE (id, workspace_id),
    CONSTRAINT fk_task_project_ws FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects (id, workspace_id) ON DELETE CASCADE,
    CONSTRAINT fk_task_weekly_commitment_ws FOREIGN KEY (weekly_commitment_id, workspace_id) REFERENCES operating.weekly_commitments (id, workspace_id) ON DELETE SET NULL,
    CONSTRAINT fk_task_initiative_ws FOREIGN KEY (initiative_id, workspace_id) REFERENCES strategy.initiatives (id, workspace_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_function ON operating.tasks USING btree (function);
CREATE INDEX IF NOT EXISTS idx_tasks_workspace_project ON operating.tasks USING btree (workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_commitment ON operating.tasks USING btree (workspace_id, weekly_commitment_id);


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

CREATE TABLE IF NOT EXISTS operating.runtime_source_signals (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  source_kind TEXT NOT NULL,
  source_id TEXT NOT NULL,
  sequence BIGINT NOT NULL,
  state TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  correlation_id TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, source_kind, source_id, sequence)
);

CREATE INDEX IF NOT EXISTS idx_runtime_source_signals_lookup ON operating.runtime_source_signals(workspace_id, source_kind, source_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS operating.runtime_snoozes (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  actor_member_id BIGINT NOT NULL,
  source_kind TEXT NOT NULL,
  source_id TEXT NOT NULL,
  snoozed_until TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, actor_member_id, source_kind, source_id)
);

CREATE INDEX IF NOT EXISTS idx_runtime_snoozes_actor ON operating.runtime_snoozes(workspace_id, actor_member_id, snoozed_until);

-- ---------------------------------------------------------------------------
-- Từ migration 14 — Bảng liên kết many-to-many Task/Objective <-> Project.
-- Composite FK (…, workspace_id) chặn liên kết chéo workspace ngay tầng DB.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operating.commitment_key_results (
    workspace_id bigint NOT NULL,
    commitment_id bigint NOT NULL,
    key_result_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS operating.cycle_key_results (
    workspace_id bigint NOT NULL,
    cycle_id bigint NOT NULL,
    key_result_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS operating.execution_plan_items (
    id bigint NOT NULL,
    plan_id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    title text NOT NULL,
    decision_reason text NOT NULL,
    evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    owner_agent_profile text,
    expected_capability text,
    autonomy_class text NOT NULL,
    autonomy_class_source text NOT NULL,
    priority text DEFAULT 'medium'::text,
    depends_on_item_ids jsonb DEFAULT '[]'::jsonb,
    sort_key double precision,
    materialized_task_id bigint,
    status text DEFAULT 'proposed'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS operating.execution_plans (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    weekly_plan_id bigint,
    goal_text text NOT NULL,
    status text DEFAULT 'draft'::text NOT NULL,
    origin text NOT NULL,
    origin_ref text,
    run_id text,
    accepted_by_member_id bigint,
    accepted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS operating.kr_contribution_assessments (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    assessment_id bigint NOT NULL,
    kr_link_id bigint,
    key_result_id bigint,
    state character varying(24) DEFAULT 'PROPOSED'::character varying NOT NULL,
    claimed_effect jsonb DEFAULT '{}'::jsonb NOT NULL,
    evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    causal_confidence double precision,
    verified_by_member_id bigint,
    verified_at timestamp with time zone,
    reason text,
    version integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS operating.kr_observations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workspace_id bigint NOT NULL,
    kr_id bigint NOT NULL,
    value_decimal numeric(18,4) NOT NULL,
    measurement_at timestamp with time zone NOT NULL,
    window_start timestamp with time zone,
    window_end timestamp with time zone,
    evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    source_ref text,
    recorded_by bigint,
    metric_contract_version integer,
    idempotency_key text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS operating.outcome_analysis_requests (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    task_result_id bigint NOT NULL,
    contract_id bigint NOT NULL,
    contract_revision integer NOT NULL,
    analysis_kind character varying(32) NOT NULL,
    analysis_policy character varying(20) NOT NULL,
    status character varying(32) DEFAULT 'QUEUED'::character varying NOT NULL,
    selected_agent_instance_id text,
    selected_assignment_id text,
    selected_run_id text,
    skill_id text,
    skill_version text,
    definition_hash text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS operating.outcome_assessments (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    request_id bigint NOT NULL,
    task_result_id bigint NOT NULL,
    contract_id bigint NOT NULL,
    agent_instance_id text NOT NULL,
    assignment_id text NOT NULL,
    run_id text NOT NULL,
    skill_id text NOT NULL,
    skill_version text NOT NULL,
    definition_hash text NOT NULL,
    rubric_version text,
    evidence_used_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    missing_evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    expected_vs_actual jsonb DEFAULT '{}'::jsonb NOT NULL,
    criterion_scores jsonb DEFAULT '{}'::jsonb NOT NULL,
    confidence double precision,
    risk_flags jsonb DEFAULT '[]'::jsonb NOT NULL,
    causal_limits jsonb DEFAULT '[]'::jsonb NOT NULL,
    next_action_proposals jsonb DEFAULT '[]'::jsonb NOT NULL,
    recommendation character varying(24) NOT NULL,
    status character varying(16) DEFAULT 'READY'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS operating.task_dependencies (
    id bigint NOT NULL,
    task_id bigint NOT NULL,
    depends_on_task_id bigint NOT NULL,
    dependency_type character varying(50) DEFAULT 'BLOCKS'::character varying,
    status character varying(50) DEFAULT 'PENDING'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS operating.task_execution_records (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    task_id bigint NOT NULL,
    run_id text,
    tool_call_id text,
    capability_id text NOT NULL,
    triggered_by_kind text NOT NULL,
    decision_record_id bigint,
    status text DEFAULT 'SUCCESS'::text NOT NULL,
    error_details jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT task_execution_records_status_check CHECK ((status = ANY (ARRAY['SUCCESS'::text, 'FAILED'::text]))),
    CONSTRAINT task_execution_records_triggered_by_kind_check CHECK ((triggered_by_kind = ANY (ARRAY['agent'::text, 'founder'::text, 'workflow'::text, 'system'::text])))
);

CREATE TABLE IF NOT EXISTS operating.task_outcome_contracts (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    task_id bigint NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    status character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    outcome_type character varying(20) NOT NULL,
    expected_outcome text NOT NULL,
    acceptance_criteria jsonb DEFAULT '{}'::jsonb NOT NULL,
    expected_evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    measurement_plan jsonb,
    impact_hypothesis text NOT NULL,
    service_objective text,
    primary_kr_id bigint,
    initiative_id bigint,
    proposed_by_agent_instance_id text,
    created_by_member_id bigint,
    confirmed_by_member_id bigint,
    confirmed_at timestamp with time zone,
    supersedes_contract_id bigint,
    change_reason text,
    version integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT task_outcome_contracts_outcome_type_check CHECK (((outcome_type)::text = ANY ((ARRAY['DIRECT_KR'::character varying, 'ENABLING_KR'::character varying, 'VALIDATION'::character varying, 'BAU'::character varying])::text[]))),
    CONSTRAINT task_outcome_contracts_status_check CHECK (((status)::text = ANY ((ARRAY['DRAFT'::character varying, 'CONFIRMED'::character varying, 'SUPERSEDED'::character varying])::text[])))
);

CREATE TABLE IF NOT EXISTS operating.task_outcome_kr_links (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    contract_id bigint NOT NULL,
    key_result_id bigint NOT NULL,
    relation_type character varying(20) NOT NULL,
    is_primary boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT task_outcome_kr_links_relation_type_check CHECK (((relation_type)::text = ANY ((ARRAY['DIRECT'::character varying, 'ENABLING'::character varying, 'VALIDATION'::character varying])::text[])))
);

CREATE TABLE IF NOT EXISTS operating.task_outcome_reviews (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    task_result_id bigint NOT NULL,
    assessment_id bigint,
    expected_result_revision integer NOT NULL,
    reviewer_member_id bigint,
    decision character varying(16) NOT NULL,
    reason_code text NOT NULL,
    narrative text,
    supersedes_review_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT task_outcome_reviews_decision_check CHECK (((decision)::text = ANY ((ARRAY['ACCEPT'::character varying, 'REWORK'::character varying, 'REJECT'::character varying])::text[])))
);

CREATE TABLE IF NOT EXISTS operating.task_results (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    task_id bigint NOT NULL,
    contract_id bigint NOT NULL,
    result_revision integer NOT NULL,
    submitted_by_kind character varying(16) NOT NULL,
    submitted_by_id text,
    work_attempt_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    summary text NOT NULL,
    structured_outputs jsonb DEFAULT '{}'::jsonb NOT NULL,
    artifact_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    claimed_measurements jsonb DEFAULT '{}'::jsonb NOT NULL,
    blockers jsonb DEFAULT '[]'::jsonb NOT NULL,
    idempotency_key text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS operating.task_schedules (
    id bigint NOT NULL,
    task_id bigint NOT NULL,
    schedule_type character varying(50) DEFAULT 'once'::character varying NOT NULL,
    cron_expr character varying(100),
    next_run_at timestamp with time zone,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS operating.task_work_packages (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    task_id bigint NOT NULL,
    outcome_contract_id bigint NOT NULL,
    title text,
    objective text NOT NULL,
    input_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    output_contract jsonb DEFAULT '{}'::jsonb NOT NULL,
    acceptance_rubric jsonb DEFAULT '{}'::jsonb NOT NULL,
    requested_by_manager_id bigint,
    assigned_agent_instance_id text NOT NULL,
    requested_priority character varying(4) NOT NULL,
    effective_priority character varying(4) NOT NULL,
    priority_reason text,
    status character varying(30) DEFAULT 'QUEUED'::character varying NOT NULL,
    dependency_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    review_due_at timestamp with time zone,
    budget_limit numeric,
    idempotency_key text,
    version integer DEFAULT 1 NOT NULL,
    queued_at timestamp with time zone DEFAULT now() NOT NULL,
    due_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT task_work_packages_effective_priority_check CHECK (((effective_priority)::text = ANY ((ARRAY['P0'::character varying, 'P1'::character varying, 'P2'::character varying, 'P3'::character varying])::text[]))),
    CONSTRAINT task_work_packages_requested_priority_check CHECK (((requested_priority)::text = ANY ((ARRAY['P0'::character varying, 'P1'::character varying, 'P2'::character varying, 'P3'::character varying])::text[]))),
    CONSTRAINT task_work_packages_status_check CHECK (((status)::text = ANY ((ARRAY['QUEUED'::character varying, 'LEASED'::character varying, 'RUNNING'::character varying, 'VALIDATION_PASSED'::character varying, 'PENDING_MANAGER_REVIEW'::character varying, 'ESCALATED_TO_FOUNDER'::character varying, 'ACCEPTED'::character varying, 'REWORK'::character varying, 'REJECTED'::character varying, 'BLOCKED'::character varying, 'ON_HOLD'::character varying, 'CANCELLED'::character varying])::text[])))
);

CREATE TABLE IF NOT EXISTS operating.work_package_attempts (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    work_package_id bigint NOT NULL,
    sequence_no integer NOT NULL,
    assigned_agent_instance_id text NOT NULL,
    assignment_snapshot jsonb,
    spec_snapshot jsonb,
    run_id text,
    status character varying(30) DEFAULT 'ACTIVE'::character varying NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    ended_at timestamp with time zone,
    ended_reason text
);

CREATE TABLE IF NOT EXISTS operating.work_package_events (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    work_package_id bigint NOT NULL,
    event_type text NOT NULL,
    actor_kind text NOT NULL,
    actor_id text,
    before_json jsonb,
    after_json jsonb,
    reason text,
    correlation_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS operating.work_package_priority_events (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    work_package_id bigint NOT NULL,
    actor_member_id bigint,
    requested_priority character varying(4) NOT NULL,
    prior_effective_priority character varying(4) NOT NULL,
    new_effective_priority character varying(4) NOT NULL,
    reason text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS operating.work_package_reviews (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    work_package_id bigint NOT NULL,
    work_attempt_id bigint,
    reviewer_member_id bigint,
    reviewer_kind character varying(16) DEFAULT 'manager'::character varying NOT NULL,
    artifact_version_ref text NOT NULL,
    decision character varying(16) NOT NULL,
    rubric_scores jsonb DEFAULT '{}'::jsonb NOT NULL,
    reason_code text NOT NULL,
    narrative text,
    supersedes_review_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT work_package_reviews_decision_check CHECK (((decision)::text = ANY ((ARRAY['ACCEPT'::character varying, 'REWORK'::character varying, 'REJECT'::character varying])::text[])))
);

CREATE TABLE IF NOT EXISTS operating.workspace_capability_policy (
    workspace_id bigint NOT NULL,
    capability_id text NOT NULL,
    decision text NOT NULL,
    updated_by bigint,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS operating.workspace_execution_settings (
    workspace_id bigint NOT NULL,
    sweep_enabled boolean DEFAULT true NOT NULL,
    updated_by bigint,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);
