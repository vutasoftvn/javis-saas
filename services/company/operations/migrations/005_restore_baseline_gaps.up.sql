-- SP-A Task 5C3 — Khôi phục 53 bảng `operating.*` / `strategy.*` bị bỏ rơi trong
-- đợt squash baseline Founder Trial R1 (`pg_dump --schema-only`, commit 81461673).
--
-- Bản squash gộp toàn bộ lịch sử migration operations thành `001` nhưng chỉ tạo
-- ~15 / ~78 bảng mà `services/company/shared/db/schema/operations.ts` +
-- `strategy.ts` khai báo. `003_cosa_automation_mvp` + `004_restore_baseline_gaps`
-- (Task 5B) khôi phục thêm vài bảng. `operating` + `strategy` là schema RETAINED
-- của R1 và Drizzle schema là nguồn sự thật R1 (quyết định người dùng 2026-09-10)
-- — file `005` này tạo lại 53 bảng còn thiếu (xem `005_restore_baseline_gaps.down.sql`
-- để có danh sách đầy đủ). `automation_definitions/_invocations/_revisions/`
-- `_invocation_events` KHÔNG nằm trong bộ này (đã do `003` tạo).
--
-- Nguồn DDL: schema-only `pg_dump` của DB dev `workspace` (còn giữ nguyên schema
-- pre-squash đầy đủ: `operating` 35 bảng, `strategy` 43 bảng) — được reset spec
-- §7.3 cho phép dùng làm "comparison aid for constraints and indexes". Cột / kiểu /
-- DEFAULT / NOT NULL / CHECK / PK sao chép verbatim từ dump; đã đối chiếu ~10 bảng
-- (strategy.okr_objectives, key_results, initiatives, tows_options,
-- next_action_rankings; operating.execution_plans, task_work_packages,
-- work_package_events, workspace_capability_policy, task_dependencies) với file
-- `.ts` — Drizzle thắng khi bất đồng; không có bất đồng cột/kiểu/nullability nào.
--
-- Expand-only + idempotent: mọi `CREATE TABLE`/`CREATE INDEX` dùng `IF NOT EXISTS`;
-- mọi PK bọc guard theo `pg_constraint` (thêm PK lần 2 raise
-- `invalid_table_definition`, KHÔNG phải `duplicate_object`); mọi UNIQUE/FK bọc
-- `DO ... EXCEPTION WHEN duplicate_object / duplicate_table THEN NULL` (từng câu,
-- không phải loop mức khối). Không INSERT/UPDATE/DELETE, không
-- DROP/RENAME/TRUNCATE, không SET NOT NULL trên cột đã có.
--
-- PK `id bigint` do app cấp (Snowflake). Dump có 24 `CREATE SEQUENCE ... OWNED BY`
-- nhưng KHÔNG có `ALTER COLUMN id SET DEFAULT nextval(...)` và KHÔNG có `ADD
-- GENERATED ... AS IDENTITY` — sequence là orphan không nối default vào cột nên bị
-- BỎ toàn bộ, khớp `.primaryKey()` trần trong `.ts` và đúng tiền lệ Task 5C / 5C2.
--
-- FK bị BỎ so với dump: KHÔNG có. 8 FK `*_workspace_id_fkey -> core.workspaces(id)`
-- (bsc_focus_scopes, initiative_key_results, pestel_signals,
-- resource_capability_assessments, strategic_objectives, swot_items,
-- tows_option_evaluations, tows_options) ĐƯỢC GIỮ: `core.workspaces` do
-- `identity/001` tạo và `operations/001` đã có tiền lệ FK sang `core.workspaces`
-- (workspace_strategy_settings); `strategy.ts` cũng khai `.references(() =>
-- identityWorkspaces.id)` cho các cột này.
--
-- FK "ngược chiều" (bảng con ở `001`/`004`, bảng cha ở `005`) — thêm ở CUỐI phần FK:
--   * operating.tasks.initiative_id            -> strategy.initiatives(id)      (fk_tasks_initiative_id, operations.ts:46)
--   * operating.weekly_commitments.initiative_id -> strategy.initiatives(id)     (weekly_commitments_initiative_id_fkey, operations.ts)
--   * strategy.decision_records.gate_evaluation_id -> strategy.gate_evaluations(id) (decision_records_gate_evaluation_id_fkey, strategy.ts:159)
--   * strategy.projects.(portfolio_id, workspace_id) -> strategy.portfolios(id, workspace_id) (fk_projects_portfolio_ws, operations.ts projects.portfolioFk)
--   * strategy.okr_objective_projects.(objective_id, workspace_id) -> strategy.okr_objectives(id, workspace_id) (fk_okr_objective_projects_objective) —
--     Drizzle KHÔNG khai FK cho link table này, nhưng dump pre-squash + migration 14 gốc CÓ,
--     `004` report hẹn thêm lại khi `okr_objectives` được khôi phục, và
--     `operations/tests/link-tables-schema.test.ts` kỳ vọng fkCount == 2 → khôi phục.
-- KHÔNG thêm lại (dump có, Drizzle KHÔNG khai, không test nào yêu cầu):
--   * operating.tasks.active_outcome_contract_id -> operating.task_outcome_contracts (tasks.activeOutcomeContractId là bigint trần)

-- =========================================================================
-- 1. CREATE TABLE (53 bảng còn thiếu — cha trước con theo thứ tự dump)
-- =========================================================================

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

CREATE TABLE IF NOT EXISTS strategy.bsc_focus_scopes (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    strategic_objective_id bigint NOT NULL,
    perspective text NOT NULL,
    focus_question text,
    focus_statement text NOT NULL,
    priority integer DEFAULT 1 NOT NULL,
    status text DEFAULT 'ACTIVE'::text NOT NULL,
    created_by_member_id bigint,
    updated_by_member_id bigint,
    revision integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT bsc_focus_scopes_perspective_check CHECK ((perspective = ANY (ARRAY['FINANCIAL'::text, 'CUSTOMER'::text, 'INTERNAL_PROCESS'::text, 'LEARNING_AND_GROWTH'::text]))),
    CONSTRAINT bsc_focus_scopes_status_check CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'INACTIVE'::text, 'ARCHIVED'::text])))
);

CREATE TABLE IF NOT EXISTS strategy.discovery_signals (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    signal_type character varying(50) NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    source text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS strategy.gate_evaluations (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    stage_policy_id bigint,
    requirements_met boolean DEFAULT false NOT NULL,
    evidence_score double precision DEFAULT 0.0 NOT NULL,
    blocking_risks jsonb DEFAULT '[]'::jsonb NOT NULL,
    result character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    rationale text DEFAULT ''::text NOT NULL,
    human_override boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    provenance_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    decision_id bigint,
    expected_stage_version integer
);

CREATE TABLE IF NOT EXISTS strategy.initiative_key_results (
    workspace_id bigint NOT NULL,
    initiative_id bigint NOT NULL,
    key_result_id bigint NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy.initiatives (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint,
    title text NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    owner_member_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    strategic_objective_id bigint,
    source_tows_option_id bigint,
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
    CONSTRAINT initiatives_approval_status_check CHECK ((approval_status = ANY (ARRAY['DRAFT'::text, 'PENDING_APPROVAL'::text, 'APPROVED'::text, 'REJECTED'::text, 'CLOSED'::text])))
);

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
    evidence_refs jsonb,
    status text DEFAULT 'draft'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    scoring_type character varying(50) DEFAULT 'LINEAR_INCREASE'::character varying NOT NULL,
    metric_contract_version integer
);

CREATE TABLE IF NOT EXISTS strategy.maturity_assessments (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    scoreboard_run_id bigint,
    dimensions jsonb DEFAULT '{}'::jsonb NOT NULL,
    assessed_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy.metric_contracts (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    metric_key character varying(100) NOT NULL,
    display_name text NOT NULL,
    unit character varying(50) NOT NULL,
    numerator_definition text NOT NULL,
    denominator_definition text NOT NULL,
    cohort_definition text NOT NULL,
    source_mapping jsonb DEFAULT '{}'::jsonb NOT NULL,
    cadence character varying(50) NOT NULL,
    fresh_until timestamp with time zone,
    guardrail text,
    owner_member_id bigint,
    decision_use text NOT NULL,
    status character varying(50) DEFAULT 'DRAFT'::character varying NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    approval_ref text,
    change_rationale text,
    created_by_member_id bigint,
    published_by_member_id bigint,
    published_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS strategy.metric_snapshots (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    contract_version_id bigint NOT NULL,
    source_system character varying(50) NOT NULL,
    source_window character varying(50) NOT NULL,
    source_record_id text NOT NULL,
    payload_hash text NOT NULL,
    observed_at timestamp with time zone NOT NULL,
    captured_at timestamp with time zone DEFAULT now() NOT NULL,
    value double precision NOT NULL,
    numerator double precision,
    denominator double precision,
    quality_status character varying(30) DEFAULT 'VALID'::character varying NOT NULL,
    quality_checks jsonb DEFAULT '{}'::jsonb NOT NULL,
    evidence_ingestion_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT metric_snapshots_quality_chk CHECK (((quality_status)::text = ANY ((ARRAY['VALID'::character varying, 'STALE'::character varying, 'INCOMPLETE'::character varying, 'REJECTED'::character varying])::text[])))
);

CREATE TABLE IF NOT EXISTS strategy.next_action_candidates (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    source character varying(50) NOT NULL,
    score double precision DEFAULT 0.0 NOT NULL,
    rationale text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS strategy.next_action_rankings (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    candidate_id bigint NOT NULL,
    rank integer NOT NULL,
    llm_rerank_note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS strategy.next_best_actions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    source text NOT NULL,
    recommendation text NOT NULL,
    priority integer DEFAULT 1 NOT NULL,
    due_by date,
    status text DEFAULT 'PROPOSED'::text NOT NULL,
    capability_required text,
    decision_reason text NOT NULL,
    context_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    regulation_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    project_id bigint,
    decision_id bigint,
    revision integer DEFAULT 1 NOT NULL,
    CONSTRAINT next_best_actions_source_check CHECK ((source = ANY (ARRAY['evidence'::text, 'finance'::text, 'legal'::text, 'stage'::text]))),
    CONSTRAINT next_best_actions_status_check CHECK ((status = ANY (ARRAY['PROPOSED'::text, 'ACCEPTED'::text, 'REJECTED'::text, 'DONE'::text])))
);

CREATE TABLE IF NOT EXISTS strategy.okr_cycles (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    name text NOT NULL,
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    status text DEFAULT 'draft'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS strategy.okr_objectives (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    cycle_id bigint NOT NULL,
    strategic_objective_id bigint,
    title text NOT NULL,
    why text,
    owner_member_id bigint,
    status text DEFAULT 'draft'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    tows_option_id bigint,
    published_by_member_id bigint,
    published_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS strategy.pestel_signals (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    strategic_objective_id bigint NOT NULL,
    dimension text NOT NULL,
    statement text NOT NULL,
    impact text NOT NULL,
    certainty text NOT NULL,
    evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    bsc_perspectives jsonb DEFAULT '[]'::jsonb NOT NULL,
    status text DEFAULT 'DRAFT'::text NOT NULL,
    created_by_member_id bigint,
    updated_by_member_id bigint,
    revision integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT pestel_signals_certainty_check CHECK ((certainty = ANY (ARRAY['HIGH'::text, 'MEDIUM'::text, 'LOW'::text]))),
    CONSTRAINT pestel_signals_dimension_check CHECK ((dimension = ANY (ARRAY['POLITICAL'::text, 'ECONOMIC'::text, 'SOCIAL'::text, 'TECHNOLOGICAL'::text, 'ENVIRONMENTAL'::text, 'LEGAL'::text]))),
    CONSTRAINT pestel_signals_impact_check CHECK ((impact = ANY (ARRAY['HIGH'::text, 'MEDIUM'::text, 'LOW'::text, 'POSITIVE'::text, 'NEGATIVE'::text]))),
    CONSTRAINT pestel_signals_status_check CHECK ((status = ANY (ARRAY['DRAFT'::text, 'ACTIVE'::text, 'ARCHIVED'::text])))
);

CREATE TABLE IF NOT EXISTS strategy.pilot_runs (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    experiment_id bigint,
    status character varying(50) DEFAULT 'DRAFT'::character varying NOT NULL,
    design_partner_evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    metric_contract_artifact_ref text,
    instrumentation_artifact_ref text,
    onboarding_artifact_ref text,
    support_escalation_artifact_ref text,
    rollback_artifact_ref text,
    release_owner_member_id bigint NOT NULL,
    approved_by_member_id bigint,
    approval_ref text,
    approved_at timestamp with time zone,
    activated_by_member_id bigint,
    activated_at timestamp with time zone,
    completed_at timestamp with time zone,
    cancelled_at timestamp with time zone,
    cancellation_reason text,
    version integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT pilot_runs_status_chk CHECK (((status)::text = ANY ((ARRAY['DRAFT'::character varying, 'APPROVED'::character varying, 'ACTIVE'::character varying, 'COMPLETED'::character varying, 'CANCELLED'::character varying])::text[])))
);

CREATE TABLE IF NOT EXISTS strategy.pmf_scoreboard_runs (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    contract_version_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    input_snapshot_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    reviewed_evidence_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    policy_version text DEFAULT 'v1'::text NOT NULL,
    score_components jsonb DEFAULT '[]'::jsonb NOT NULL,
    missing_data_flags jsonb DEFAULT '[]'::jsonb NOT NULL,
    reliability_flags jsonb DEFAULT '[]'::jsonb NOT NULL,
    calculation_hash text NOT NULL,
    result character varying(50) NOT NULL,
    human_review_state jsonb DEFAULT '{}'::jsonb NOT NULL,
    calculated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT pmf_scoreboard_result_chk CHECK (((result)::text = ANY ((ARRAY['INSUFFICIENT_DATA'::character varying, 'MIXED'::character varying, 'PROMISING'::character varying, 'CONCERNING'::character varying])::text[])))
);

CREATE TABLE IF NOT EXISTS strategy.portfolio_projects (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    portfolio_id bigint NOT NULL,
    project_id bigint NOT NULL,
    strategic_priority character varying(50) DEFAULT 'core'::character varying NOT NULL,
    capacity_allocation double precision DEFAULT 0.0 NOT NULL,
    founder_attention_hours double precision DEFAULT 0.0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS strategy.portfolios (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    strategic_focus character varying(255),
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS strategy.project_stage_transition_policies (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint,
    from_stage character varying(50) NOT NULL,
    to_stage character varying(50) NOT NULL,
    allowed boolean DEFAULT true NOT NULL,
    policy_version text DEFAULT 'v1'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS strategy.project_stage_transitions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint NOT NULL,
    from_stage character varying(50) NOT NULL,
    to_stage character varying(50) NOT NULL,
    reason text NOT NULL,
    actor_member_id bigint,
    actor_role text,
    override_flag boolean DEFAULT false NOT NULL,
    override_approval_ref text,
    source text DEFAULT 'manual'::text NOT NULL,
    stage_version_from integer,
    policy_version text,
    evidence_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    evaluation_result jsonb,
    decided_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    provenance_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    decision_id bigint,
    expected_stage_version integer,
    CONSTRAINT project_stage_transitions_source_chk CHECK ((source = ANY (ARRAY['manual'::text, 'autonomous'::text, 'api'::text, 'system'::text])))
);

CREATE TABLE IF NOT EXISTS strategy.resource_capability_assessments (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    strategic_objective_id bigint NOT NULL,
    category text NOT NULL,
    statement text NOT NULL,
    strength_level text NOT NULL,
    evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    bsc_perspectives jsonb DEFAULT '[]'::jsonb NOT NULL,
    status text DEFAULT 'DRAFT'::text NOT NULL,
    created_by_member_id bigint,
    updated_by_member_id bigint,
    revision integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT resource_capability_assessments_category_check CHECK ((category = ANY (ARRAY['FINANCIAL_RESOURCE'::text, 'HUMAN_ORGANIZATIONAL_CAPABILITY'::text, 'INTELLECTUAL_DATA_IP_ASSET'::text, 'TECHNOLOGY_OPERATIONAL_ASSET'::text, 'MARKET_RELATIONSHIP_ASSET'::text, 'GOVERNANCE_LEGAL_RISK_CAPABILITY'::text]))),
    CONSTRAINT resource_capability_assessments_status_check CHECK ((status = ANY (ARRAY['DRAFT'::text, 'ACTIVE'::text, 'ARCHIVED'::text]))),
    CONSTRAINT resource_capability_assessments_strength_level_check CHECK ((strength_level = ANY (ARRAY['STRONG'::text, 'ADEQUATE'::text, 'WEAK'::text])))
);

CREATE TABLE IF NOT EXISTS strategy.stage_policies (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    stage_key character varying(50) NOT NULL,
    requirements jsonb DEFAULT '[]'::jsonb NOT NULL,
    minimum_evidence_score double precision DEFAULT 0.0 NOT NULL,
    blocking_risk_rules jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

CREATE TABLE IF NOT EXISTS strategy.stage_transition_policies (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    from_stage character varying(50) NOT NULL,
    to_stage character varying(50) NOT NULL,
    policy_id bigint,
    allowed boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    policy_version text DEFAULT 'v1'::text NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy.strategic_objectives (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    project_id bigint,
    title text NOT NULL,
    success_definition text,
    time_horizon_end timestamp with time zone,
    status text DEFAULT 'DRAFT'::text NOT NULL,
    owner_member_id bigint,
    settings_revision integer,
    created_by_member_id bigint,
    updated_by_member_id bigint,
    revision integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT strategic_objectives_status_check CHECK ((status = ANY (ARRAY['DRAFT'::text, 'ACTIVE'::text, 'ARCHIVED'::text])))
);

CREATE TABLE IF NOT EXISTS strategy.swot_items (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    strategic_objective_id bigint NOT NULL,
    kind text NOT NULL,
    statement text NOT NULL,
    source_type text NOT NULL,
    source_id bigint,
    evidence_refs jsonb DEFAULT '[]'::jsonb NOT NULL,
    bsc_perspectives jsonb DEFAULT '[]'::jsonb NOT NULL,
    status text DEFAULT 'DRAFT'::text NOT NULL,
    created_by_member_id bigint,
    updated_by_member_id bigint,
    revision integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT swot_items_kind_check CHECK ((kind = ANY (ARRAY['STRENGTH'::text, 'WEAKNESS'::text, 'OPPORTUNITY'::text, 'THREAT'::text]))),
    CONSTRAINT swot_items_source_type_check CHECK ((source_type = ANY (ARRAY['PESTEL_SIGNAL'::text, 'RESOURCE_CAPABILITY'::text, 'MANUAL'::text]))),
    CONSTRAINT swot_items_status_check CHECK ((status = ANY (ARRAY['DRAFT'::text, 'ACTIVE'::text, 'ARCHIVED'::text])))
);

CREATE TABLE IF NOT EXISTS strategy.tows_option_evaluations (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    tows_option_id bigint NOT NULL,
    impact_score integer NOT NULL,
    difficulty_score integer NOT NULL,
    rationale text,
    scored_by_member_id bigint,
    scorer_kind text DEFAULT 'HUMAN'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tows_option_evaluations_difficulty_score_check CHECK (((difficulty_score >= 1) AND (difficulty_score <= 5))),
    CONSTRAINT tows_option_evaluations_impact_score_check CHECK (((impact_score >= 1) AND (impact_score <= 5))),
    CONSTRAINT tows_option_evaluations_scorer_kind_check CHECK ((scorer_kind = ANY (ARRAY['HUMAN'::text, 'AI_AGENT'::text])))
);

CREATE TABLE IF NOT EXISTS strategy.tows_options (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    strategic_objective_id bigint NOT NULL,
    quadrant text NOT NULL,
    title text NOT NULL,
    rationale text,
    swot_item_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    status text DEFAULT 'DRAFT'::text NOT NULL,
    ai_provenance jsonb,
    selected_by_member_id bigint,
    selected_at timestamp with time zone,
    decision_id bigint,
    created_by_member_id bigint,
    updated_by_member_id bigint,
    revision integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tows_options_quadrant_check CHECK ((quadrant = ANY (ARRAY['SO'::text, 'WO'::text, 'ST'::text, 'WT'::text]))),
    CONSTRAINT tows_options_status_check CHECK ((status = ANY (ARRAY['DRAFT'::text, 'PROPOSED'::text, 'SELECTED'::text, 'REJECTED'::text, 'SUPERSEDED'::text])))
);

CREATE TABLE IF NOT EXISTS strategy.venture_profiles (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    problem_statement text,
    target_customer text,
    industry text,
    geography text,
    currency text DEFAULT 'VND'::text,
    timezone text DEFAULT 'Asia/Ho_Chi_Minh'::text,
    founder_goal character varying(50),
    initial_runway_months integer,
    stage_entered_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy.weekly_reviews (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    week_start_date date NOT NULL,
    summary text NOT NULL,
    stage_assessment text,
    cash_summary text,
    obligations_summary text,
    action_proposals jsonb DEFAULT '[]'::jsonb NOT NULL,
    status text DEFAULT 'DRAFT'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    weekly_plan_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    decision_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    CONSTRAINT weekly_reviews_status_check CHECK ((status = ANY (ARRAY['DRAFT'::text, 'COMPLETED'::text])))
);

CREATE TABLE IF NOT EXISTS strategy.workspace_stage_transitions (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    from_stage character varying(50) NOT NULL,
    to_stage character varying(50) NOT NULL,
    reason text NOT NULL,
    actor_member_id bigint,
    override_flag boolean DEFAULT false NOT NULL,
    decided_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    stage_version_from integer,
    source text DEFAULT 'manual'::text NOT NULL,
    actor_role text,
    policy_version text,
    override_approval_ref text,
    evidence_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    evaluation_result jsonb,
    provenance_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    decision_id bigint,
    expected_stage_version integer,
    CONSTRAINT workspace_stage_transitions_source_chk CHECK ((source = ANY (ARRAY['manual'::text, 'autonomous'::text, 'api'::text, 'system'::text])))
);

-- =========================================================================
-- 2. CREATE INDEX (chỉ index của 53 bảng trên)
-- =========================================================================

CREATE INDEX IF NOT EXISTS ix_execution_plan_items_materialized_task ON operating.execution_plan_items USING btree (materialized_task_id) WHERE (materialized_task_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS ix_execution_plan_items_plan ON operating.execution_plan_items USING btree (plan_id);
CREATE INDEX IF NOT EXISTS ix_execution_plans_project_status ON operating.execution_plans USING btree (project_id, status) WHERE (deleted_at IS NULL);
CREATE UNIQUE INDEX IF NOT EXISTS uix_execution_plans_one_draft_per_weekly_plan ON operating.execution_plans USING btree (weekly_plan_id) WHERE ((status = 'draft'::text) AND (deleted_at IS NULL));
CREATE INDEX IF NOT EXISTS ix_kr_contribution_assessments_assessment ON operating.kr_contribution_assessments USING btree (assessment_id, state);
CREATE INDEX IF NOT EXISTS idx_kr_observations_kr_measurement ON operating.kr_observations USING btree (workspace_id, kr_id, measurement_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uix_kr_observations_ws_kr_idempotency ON operating.kr_observations USING btree (workspace_id, kr_id, idempotency_key) WHERE (idempotency_key IS NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS uix_outcome_analysis_requests_idem ON operating.outcome_analysis_requests USING btree (workspace_id, task_result_id, analysis_kind, contract_revision);
CREATE INDEX IF NOT EXISTS ix_outcome_assessments_result ON operating.outcome_assessments USING btree (task_result_id, status);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_depends_on ON operating.task_dependencies USING btree (depends_on_task_id);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_task_id ON operating.task_dependencies USING btree (task_id);
CREATE INDEX IF NOT EXISTS idx_task_execution_records_ws_task ON operating.task_execution_records USING btree (workspace_id, task_id);
CREATE INDEX IF NOT EXISTS ix_task_outcome_contracts_ws_task ON operating.task_outcome_contracts USING btree (workspace_id, task_id, status);
CREATE UNIQUE INDEX IF NOT EXISTS uix_task_outcome_contracts_active_confirmed ON operating.task_outcome_contracts USING btree (task_id) WHERE ((status)::text = 'CONFIRMED'::text);
CREATE UNIQUE INDEX IF NOT EXISTS uix_task_outcome_contracts_task_revision ON operating.task_outcome_contracts USING btree (task_id, revision);
CREATE UNIQUE INDEX IF NOT EXISTS uix_task_outcome_kr_links_contract_kr ON operating.task_outcome_kr_links USING btree (contract_id, key_result_id);
CREATE UNIQUE INDEX IF NOT EXISTS uix_task_outcome_kr_links_primary ON operating.task_outcome_kr_links USING btree (contract_id) WHERE (is_primary = true);
CREATE INDEX IF NOT EXISTS ix_task_outcome_reviews_result ON operating.task_outcome_reviews USING btree (task_result_id, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS uix_task_results_idem ON operating.task_results USING btree (workspace_id, idempotency_key) WHERE (idempotency_key IS NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS uix_task_results_task_revision ON operating.task_results USING btree (task_id, result_revision);
CREATE INDEX IF NOT EXISTS idx_task_schedules_task_id ON operating.task_schedules USING btree (task_id);
CREATE INDEX IF NOT EXISTS ix_task_work_packages_queue ON operating.task_work_packages USING btree (workspace_id, status, effective_priority, due_at, queued_at);
CREATE INDEX IF NOT EXISTS ix_task_work_packages_task ON operating.task_work_packages USING btree (workspace_id, task_id);
CREATE UNIQUE INDEX IF NOT EXISTS uix_task_work_packages_idem ON operating.task_work_packages USING btree (workspace_id, idempotency_key) WHERE (idempotency_key IS NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS uix_work_package_attempts_active ON operating.work_package_attempts USING btree (work_package_id) WHERE (ended_at IS NULL);
CREATE UNIQUE INDEX IF NOT EXISTS uix_work_package_attempts_seq ON operating.work_package_attempts USING btree (work_package_id, sequence_no);
CREATE INDEX IF NOT EXISTS ix_work_package_events_wp ON operating.work_package_events USING btree (work_package_id, created_at);
CREATE INDEX IF NOT EXISTS ix_work_package_priority_events_wp ON operating.work_package_priority_events USING btree (work_package_id, created_at);
CREATE INDEX IF NOT EXISTS ix_work_package_reviews_wp ON operating.work_package_reviews USING btree (work_package_id, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_bsc_focus_scopes_active ON strategy.bsc_focus_scopes USING btree (strategic_objective_id, perspective) WHERE (status = 'ACTIVE'::text);
CREATE INDEX IF NOT EXISTS idx_discovery_signals_project ON strategy.discovery_signals USING btree (project_id);
CREATE INDEX IF NOT EXISTS idx_gate_evaluations_project ON strategy.gate_evaluations USING btree (project_id);
CREATE INDEX IF NOT EXISTS idx_initiative_key_results_initiative ON strategy.initiative_key_results USING btree (workspace_id, initiative_id);
CREATE INDEX IF NOT EXISTS idx_initiative_key_results_kr ON strategy.initiative_key_results USING btree (workspace_id, key_result_id);
CREATE INDEX IF NOT EXISTS idx_initiatives_objective_approval ON strategy.initiatives USING btree (workspace_id, strategic_objective_id, approval_status);
CREATE INDEX IF NOT EXISTS idx_initiatives_workspace_id ON strategy.initiatives USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_key_results_objective_id ON strategy.key_results USING btree (objective_id);
CREATE INDEX IF NOT EXISTS idx_key_results_workspace_id ON strategy.key_results USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_maturity_assessments_run ON strategy.maturity_assessments USING btree (scoreboard_run_id);
CREATE INDEX IF NOT EXISTS idx_maturity_assessments_ws_proj ON strategy.maturity_assessments USING btree (workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_metric_contracts_key ON strategy.metric_contracts USING btree (workspace_id, metric_key);
CREATE INDEX IF NOT EXISTS idx_metric_contracts_ws_proj ON strategy.metric_contracts USING btree (workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_contract ON strategy.metric_snapshots USING btree (workspace_id, contract_version_id);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_observed ON strategy.metric_snapshots USING btree (workspace_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_ws_proj ON strategy.metric_snapshots USING btree (workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_next_action_candidates_project ON strategy.next_action_candidates USING btree (project_id);
CREATE INDEX IF NOT EXISTS idx_next_action_rankings_project ON strategy.next_action_rankings USING btree (project_id);
CREATE INDEX IF NOT EXISTS idx_next_best_actions_project_status ON strategy.next_best_actions USING btree (project_id, status);
CREATE INDEX IF NOT EXISTS idx_next_best_actions_ws_status_priority ON strategy.next_best_actions USING btree (workspace_id, status, priority);
CREATE INDEX IF NOT EXISTS idx_okr_cycles_workspace_id ON strategy.okr_cycles USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_okr_objectives_cycle_id ON strategy.okr_objectives USING btree (cycle_id);
CREATE INDEX IF NOT EXISTS idx_okr_objectives_tows_option ON strategy.okr_objectives USING btree (workspace_id, tows_option_id);
CREATE INDEX IF NOT EXISTS idx_okr_objectives_workspace_id ON strategy.okr_objectives USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_pestel_signals_objective_status ON strategy.pestel_signals USING btree (workspace_id, strategic_objective_id, status);
CREATE INDEX IF NOT EXISTS idx_pilot_runs_ws_proj ON strategy.pilot_runs USING btree (workspace_id, project_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pilot_runs_active_project ON strategy.pilot_runs USING btree (workspace_id, project_id) WHERE (((status)::text = 'ACTIVE'::text) AND (deleted_at IS NULL));
CREATE INDEX IF NOT EXISTS idx_pmf_scoreboards_hash ON strategy.pmf_scoreboard_runs USING btree (calculation_hash);
CREATE INDEX IF NOT EXISTS idx_pmf_scoreboards_ws_proj ON strategy.pmf_scoreboard_runs USING btree (workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_projects_portfolio ON strategy.portfolio_projects USING btree (portfolio_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_projects_project ON strategy.portfolio_projects USING btree (project_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_workspace ON strategy.portfolios USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_project_stage_transition_policies_ws ON strategy.project_stage_transition_policies USING btree (workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_project_stage_transitions_ws_proj_decided ON strategy.project_stage_transitions USING btree (workspace_id, project_id, decided_at);
CREATE INDEX IF NOT EXISTS idx_resource_assessments_objective_status ON strategy.resource_capability_assessments USING btree (workspace_id, strategic_objective_id, status);
CREATE INDEX IF NOT EXISTS idx_stage_policies_stage_key ON strategy.stage_policies USING btree (stage_key);
CREATE INDEX IF NOT EXISTS idx_swot_items_objective_status ON strategy.swot_items USING btree (workspace_id, strategic_objective_id, status);
CREATE INDEX IF NOT EXISTS idx_swot_items_source ON strategy.swot_items USING btree (workspace_id, source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_tows_evaluations_option ON strategy.tows_option_evaluations USING btree (workspace_id, tows_option_id);
CREATE INDEX IF NOT EXISTS idx_tows_options_objective_status ON strategy.tows_options USING btree (workspace_id, strategic_objective_id, status);
CREATE INDEX IF NOT EXISTS idx_venture_profiles_workspace ON strategy.venture_profiles USING btree (workspace_id);
CREATE INDEX IF NOT EXISTS idx_weekly_reviews_ws_date ON strategy.weekly_reviews USING btree (workspace_id, week_start_date);
CREATE INDEX IF NOT EXISTS idx_venture_stage_transitions_ws_decided ON strategy.workspace_stage_transitions USING btree (workspace_id, decided_at);

-- =========================================================================
-- 3. ADD CONSTRAINT — PRIMARY KEY (guard theo pg_constraint)
-- =========================================================================

DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.commitment_key_results'::regclass AND contype = 'p') THEN ALTER TABLE operating.commitment_key_results ADD CONSTRAINT commitment_key_results_pkey PRIMARY KEY (workspace_id, commitment_id, key_result_id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.cycle_key_results'::regclass AND contype = 'p') THEN ALTER TABLE operating.cycle_key_results ADD CONSTRAINT cycle_key_results_pkey PRIMARY KEY (workspace_id, cycle_id, key_result_id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.execution_plan_items'::regclass AND contype = 'p') THEN ALTER TABLE operating.execution_plan_items ADD CONSTRAINT execution_plan_items_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.execution_plans'::regclass AND contype = 'p') THEN ALTER TABLE operating.execution_plans ADD CONSTRAINT execution_plans_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.kr_contribution_assessments'::regclass AND contype = 'p') THEN ALTER TABLE operating.kr_contribution_assessments ADD CONSTRAINT kr_contribution_assessments_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.kr_observations'::regclass AND contype = 'p') THEN ALTER TABLE operating.kr_observations ADD CONSTRAINT kr_observations_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.outcome_analysis_requests'::regclass AND contype = 'p') THEN ALTER TABLE operating.outcome_analysis_requests ADD CONSTRAINT outcome_analysis_requests_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.outcome_assessments'::regclass AND contype = 'p') THEN ALTER TABLE operating.outcome_assessments ADD CONSTRAINT outcome_assessments_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.task_dependencies'::regclass AND contype = 'p') THEN ALTER TABLE operating.task_dependencies ADD CONSTRAINT task_dependencies_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.task_execution_records'::regclass AND contype = 'p') THEN ALTER TABLE operating.task_execution_records ADD CONSTRAINT task_execution_records_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.task_outcome_contracts'::regclass AND contype = 'p') THEN ALTER TABLE operating.task_outcome_contracts ADD CONSTRAINT task_outcome_contracts_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.task_outcome_kr_links'::regclass AND contype = 'p') THEN ALTER TABLE operating.task_outcome_kr_links ADD CONSTRAINT task_outcome_kr_links_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.task_outcome_reviews'::regclass AND contype = 'p') THEN ALTER TABLE operating.task_outcome_reviews ADD CONSTRAINT task_outcome_reviews_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.task_results'::regclass AND contype = 'p') THEN ALTER TABLE operating.task_results ADD CONSTRAINT task_results_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.task_schedules'::regclass AND contype = 'p') THEN ALTER TABLE operating.task_schedules ADD CONSTRAINT task_schedules_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.task_work_packages'::regclass AND contype = 'p') THEN ALTER TABLE operating.task_work_packages ADD CONSTRAINT task_work_packages_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.work_package_attempts'::regclass AND contype = 'p') THEN ALTER TABLE operating.work_package_attempts ADD CONSTRAINT work_package_attempts_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.work_package_events'::regclass AND contype = 'p') THEN ALTER TABLE operating.work_package_events ADD CONSTRAINT work_package_events_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.work_package_priority_events'::regclass AND contype = 'p') THEN ALTER TABLE operating.work_package_priority_events ADD CONSTRAINT work_package_priority_events_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.work_package_reviews'::regclass AND contype = 'p') THEN ALTER TABLE operating.work_package_reviews ADD CONSTRAINT work_package_reviews_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.workspace_capability_policy'::regclass AND contype = 'p') THEN ALTER TABLE operating.workspace_capability_policy ADD CONSTRAINT workspace_capability_policy_pkey PRIMARY KEY (workspace_id, capability_id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'operating.workspace_execution_settings'::regclass AND contype = 'p') THEN ALTER TABLE operating.workspace_execution_settings ADD CONSTRAINT workspace_execution_settings_pkey PRIMARY KEY (workspace_id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.bsc_focus_scopes'::regclass AND contype = 'p') THEN ALTER TABLE strategy.bsc_focus_scopes ADD CONSTRAINT bsc_focus_scopes_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.discovery_signals'::regclass AND contype = 'p') THEN ALTER TABLE strategy.discovery_signals ADD CONSTRAINT discovery_signals_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.gate_evaluations'::regclass AND contype = 'p') THEN ALTER TABLE strategy.gate_evaluations ADD CONSTRAINT gate_evaluations_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.initiative_key_results'::regclass AND contype = 'p') THEN ALTER TABLE strategy.initiative_key_results ADD CONSTRAINT initiative_key_results_pkey PRIMARY KEY (workspace_id, initiative_id, key_result_id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.initiatives'::regclass AND contype = 'p') THEN ALTER TABLE strategy.initiatives ADD CONSTRAINT initiatives_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.key_results'::regclass AND contype = 'p') THEN ALTER TABLE strategy.key_results ADD CONSTRAINT key_results_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.maturity_assessments'::regclass AND contype = 'p') THEN ALTER TABLE strategy.maturity_assessments ADD CONSTRAINT maturity_assessments_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.metric_contracts'::regclass AND contype = 'p') THEN ALTER TABLE strategy.metric_contracts ADD CONSTRAINT metric_contracts_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.metric_snapshots'::regclass AND contype = 'p') THEN ALTER TABLE strategy.metric_snapshots ADD CONSTRAINT metric_snapshots_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.next_action_candidates'::regclass AND contype = 'p') THEN ALTER TABLE strategy.next_action_candidates ADD CONSTRAINT next_action_candidates_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.next_action_rankings'::regclass AND contype = 'p') THEN ALTER TABLE strategy.next_action_rankings ADD CONSTRAINT next_action_rankings_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.next_best_actions'::regclass AND contype = 'p') THEN ALTER TABLE strategy.next_best_actions ADD CONSTRAINT next_best_actions_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.okr_cycles'::regclass AND contype = 'p') THEN ALTER TABLE strategy.okr_cycles ADD CONSTRAINT okr_cycles_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.okr_objectives'::regclass AND contype = 'p') THEN ALTER TABLE strategy.okr_objectives ADD CONSTRAINT okr_objectives_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.pestel_signals'::regclass AND contype = 'p') THEN ALTER TABLE strategy.pestel_signals ADD CONSTRAINT pestel_signals_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.pilot_runs'::regclass AND contype = 'p') THEN ALTER TABLE strategy.pilot_runs ADD CONSTRAINT pilot_runs_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.pmf_scoreboard_runs'::regclass AND contype = 'p') THEN ALTER TABLE strategy.pmf_scoreboard_runs ADD CONSTRAINT pmf_scoreboard_runs_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.portfolio_projects'::regclass AND contype = 'p') THEN ALTER TABLE strategy.portfolio_projects ADD CONSTRAINT portfolio_projects_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.portfolios'::regclass AND contype = 'p') THEN ALTER TABLE strategy.portfolios ADD CONSTRAINT portfolios_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.project_stage_transition_policies'::regclass AND contype = 'p') THEN ALTER TABLE strategy.project_stage_transition_policies ADD CONSTRAINT project_stage_transition_policies_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.project_stage_transitions'::regclass AND contype = 'p') THEN ALTER TABLE strategy.project_stage_transitions ADD CONSTRAINT project_stage_transitions_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.resource_capability_assessments'::regclass AND contype = 'p') THEN ALTER TABLE strategy.resource_capability_assessments ADD CONSTRAINT resource_capability_assessments_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.stage_policies'::regclass AND contype = 'p') THEN ALTER TABLE strategy.stage_policies ADD CONSTRAINT stage_policies_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.stage_transition_policies'::regclass AND contype = 'p') THEN ALTER TABLE strategy.stage_transition_policies ADD CONSTRAINT stage_transitions_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.strategic_objectives'::regclass AND contype = 'p') THEN ALTER TABLE strategy.strategic_objectives ADD CONSTRAINT strategic_objectives_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.swot_items'::regclass AND contype = 'p') THEN ALTER TABLE strategy.swot_items ADD CONSTRAINT swot_items_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.tows_option_evaluations'::regclass AND contype = 'p') THEN ALTER TABLE strategy.tows_option_evaluations ADD CONSTRAINT tows_option_evaluations_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.tows_options'::regclass AND contype = 'p') THEN ALTER TABLE strategy.tows_options ADD CONSTRAINT tows_options_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.venture_profiles'::regclass AND contype = 'p') THEN ALTER TABLE strategy.venture_profiles ADD CONSTRAINT venture_profiles_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.workspace_stage_transitions'::regclass AND contype = 'p') THEN ALTER TABLE strategy.workspace_stage_transitions ADD CONSTRAINT venture_stage_transitions_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'strategy.weekly_reviews'::regclass AND contype = 'p') THEN ALTER TABLE strategy.weekly_reviews ADD CONSTRAINT weekly_reviews_pkey PRIMARY KEY (id); END IF; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;

-- =========================================================================
-- 4. ADD CONSTRAINT — UNIQUE
-- =========================================================================

DO $$ BEGIN ALTER TABLE strategy.initiatives ADD CONSTRAINT uix_initiatives_id_workspace UNIQUE (id, workspace_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.key_results ADD CONSTRAINT uix_key_results_id_workspace UNIQUE (id, workspace_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.okr_objectives ADD CONSTRAINT uix_okr_objectives_id_workspace UNIQUE (id, workspace_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.portfolio_projects ADD CONSTRAINT uix_portfolio_project UNIQUE (portfolio_id, project_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.portfolios ADD CONSTRAINT uix_portfolios_id_workspace UNIQUE (id, workspace_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.tows_options ADD CONSTRAINT uix_tows_options_id_workspace UNIQUE (id, workspace_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.metric_contracts ADD CONSTRAINT uq_metric_contract_version UNIQUE (workspace_id, project_id, metric_key, version); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.metric_snapshots ADD CONSTRAINT uq_metric_snapshot_idempotent UNIQUE (workspace_id, contract_version_id, source_system, source_record_id, payload_hash); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.strategic_objectives ADD CONSTRAINT uq_strategic_objectives_workspace UNIQUE (id, workspace_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.venture_profiles ADD CONSTRAINT venture_profiles_workspace_id_key UNIQUE (workspace_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.weekly_reviews ADD CONSTRAINT weekly_reviews_workspace_id_week_start_date_key UNIQUE (workspace_id, week_start_date); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;

-- =========================================================================
-- 5. ADD CONSTRAINT — FOREIGN KEY (target trong bộ 53 này, trong `001`/`003`/`004`,
--    hoặc `core.workspaces`; 4 FK ngược chiều ở cuối)
-- =========================================================================

DO $$ BEGIN ALTER TABLE operating.commitment_key_results ADD CONSTRAINT commitment_key_results_commitment_id_fkey FOREIGN KEY (commitment_id) REFERENCES operating.weekly_commitments(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.commitment_key_results ADD CONSTRAINT commitment_key_results_key_result_id_fkey FOREIGN KEY (key_result_id) REFERENCES strategy.key_results(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.cycle_key_results ADD CONSTRAINT cycle_key_results_cycle_id_fkey FOREIGN KEY (cycle_id) REFERENCES operating.twelve_week_cycles(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.cycle_key_results ADD CONSTRAINT cycle_key_results_key_result_id_fkey FOREIGN KEY (key_result_id) REFERENCES strategy.key_results(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.execution_plan_items ADD CONSTRAINT execution_plan_items_materialized_task_id_fkey FOREIGN KEY (materialized_task_id) REFERENCES operating.tasks(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.execution_plan_items ADD CONSTRAINT execution_plan_items_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES operating.execution_plans(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.execution_plans ADD CONSTRAINT execution_plans_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.execution_plans ADD CONSTRAINT execution_plans_weekly_plan_id_fkey FOREIGN KEY (weekly_plan_id) REFERENCES operating.weekly_plans(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.kr_contribution_assessments ADD CONSTRAINT kr_contribution_assessments_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES operating.outcome_assessments(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.kr_contribution_assessments ADD CONSTRAINT kr_contribution_assessments_key_result_id_fkey FOREIGN KEY (key_result_id) REFERENCES strategy.key_results(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.kr_contribution_assessments ADD CONSTRAINT kr_contribution_assessments_kr_link_id_fkey FOREIGN KEY (kr_link_id) REFERENCES operating.task_outcome_kr_links(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.kr_observations ADD CONSTRAINT kr_observations_kr_id_fkey FOREIGN KEY (kr_id) REFERENCES strategy.key_results(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.outcome_analysis_requests ADD CONSTRAINT outcome_analysis_requests_contract_id_fkey FOREIGN KEY (contract_id) REFERENCES operating.task_outcome_contracts(id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.outcome_analysis_requests ADD CONSTRAINT outcome_analysis_requests_task_result_id_fkey FOREIGN KEY (task_result_id) REFERENCES operating.task_results(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.outcome_assessments ADD CONSTRAINT outcome_assessments_contract_id_fkey FOREIGN KEY (contract_id) REFERENCES operating.task_outcome_contracts(id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.outcome_assessments ADD CONSTRAINT outcome_assessments_request_id_fkey FOREIGN KEY (request_id) REFERENCES operating.outcome_analysis_requests(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.outcome_assessments ADD CONSTRAINT outcome_assessments_task_result_id_fkey FOREIGN KEY (task_result_id) REFERENCES operating.task_results(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_dependencies ADD CONSTRAINT task_dependencies_depends_on_task_id_fkey FOREIGN KEY (depends_on_task_id) REFERENCES operating.tasks(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_dependencies ADD CONSTRAINT task_dependencies_task_id_fkey FOREIGN KEY (task_id) REFERENCES operating.tasks(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_execution_records ADD CONSTRAINT task_execution_records_decision_record_id_fkey FOREIGN KEY (decision_record_id) REFERENCES strategy.decision_records(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_execution_records ADD CONSTRAINT task_execution_records_task_id_fkey FOREIGN KEY (task_id) REFERENCES operating.tasks(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_outcome_contracts ADD CONSTRAINT task_outcome_contracts_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES strategy.initiatives(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_outcome_contracts ADD CONSTRAINT task_outcome_contracts_primary_kr_id_fkey FOREIGN KEY (primary_kr_id) REFERENCES strategy.key_results(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_outcome_contracts ADD CONSTRAINT task_outcome_contracts_supersedes_contract_id_fkey FOREIGN KEY (supersedes_contract_id) REFERENCES operating.task_outcome_contracts(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_outcome_contracts ADD CONSTRAINT task_outcome_contracts_task_id_fkey FOREIGN KEY (task_id) REFERENCES operating.tasks(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_outcome_kr_links ADD CONSTRAINT task_outcome_kr_links_contract_id_fkey FOREIGN KEY (contract_id) REFERENCES operating.task_outcome_contracts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_outcome_kr_links ADD CONSTRAINT task_outcome_kr_links_key_result_id_fkey FOREIGN KEY (key_result_id) REFERENCES strategy.key_results(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_outcome_reviews ADD CONSTRAINT task_outcome_reviews_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES operating.outcome_assessments(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_outcome_reviews ADD CONSTRAINT task_outcome_reviews_supersedes_review_id_fkey FOREIGN KEY (supersedes_review_id) REFERENCES operating.task_outcome_reviews(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_outcome_reviews ADD CONSTRAINT task_outcome_reviews_task_result_id_fkey FOREIGN KEY (task_result_id) REFERENCES operating.task_results(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_results ADD CONSTRAINT task_results_contract_id_fkey FOREIGN KEY (contract_id) REFERENCES operating.task_outcome_contracts(id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_results ADD CONSTRAINT task_results_task_id_fkey FOREIGN KEY (task_id) REFERENCES operating.tasks(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_schedules ADD CONSTRAINT task_schedules_task_id_fkey FOREIGN KEY (task_id) REFERENCES operating.tasks(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_work_packages ADD CONSTRAINT task_work_packages_outcome_contract_id_fkey FOREIGN KEY (outcome_contract_id) REFERENCES operating.task_outcome_contracts(id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.task_work_packages ADD CONSTRAINT task_work_packages_task_id_fkey FOREIGN KEY (task_id) REFERENCES operating.tasks(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.work_package_attempts ADD CONSTRAINT work_package_attempts_work_package_id_fkey FOREIGN KEY (work_package_id) REFERENCES operating.task_work_packages(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.work_package_events ADD CONSTRAINT work_package_events_work_package_id_fkey FOREIGN KEY (work_package_id) REFERENCES operating.task_work_packages(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.work_package_priority_events ADD CONSTRAINT work_package_priority_events_work_package_id_fkey FOREIGN KEY (work_package_id) REFERENCES operating.task_work_packages(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.work_package_reviews ADD CONSTRAINT work_package_reviews_supersedes_review_id_fkey FOREIGN KEY (supersedes_review_id) REFERENCES operating.work_package_reviews(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.work_package_reviews ADD CONSTRAINT work_package_reviews_work_attempt_id_fkey FOREIGN KEY (work_attempt_id) REFERENCES operating.work_package_attempts(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.work_package_reviews ADD CONSTRAINT work_package_reviews_work_package_id_fkey FOREIGN KEY (work_package_id) REFERENCES operating.task_work_packages(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.bsc_focus_scopes ADD CONSTRAINT bsc_focus_scopes_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.discovery_signals ADD CONSTRAINT discovery_signals_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.bsc_focus_scopes ADD CONSTRAINT fk_bsc_focus_scopes_objective FOREIGN KEY (strategic_objective_id, workspace_id) REFERENCES strategy.strategic_objectives(id, workspace_id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.initiative_key_results ADD CONSTRAINT fk_initiative_key_results_initiative FOREIGN KEY (initiative_id, workspace_id) REFERENCES strategy.initiatives(id, workspace_id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.initiative_key_results ADD CONSTRAINT fk_initiative_key_results_key_result FOREIGN KEY (key_result_id, workspace_id) REFERENCES strategy.key_results(id, workspace_id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.initiatives ADD CONSTRAINT fk_initiatives_strategic_objective FOREIGN KEY (strategic_objective_id, workspace_id) REFERENCES strategy.strategic_objectives(id, workspace_id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.initiatives ADD CONSTRAINT fk_initiatives_tows_option FOREIGN KEY (source_tows_option_id, workspace_id) REFERENCES strategy.tows_options(id, workspace_id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.okr_objectives ADD CONSTRAINT fk_okr_objectives_strategic_objective FOREIGN KEY (strategic_objective_id, workspace_id) REFERENCES strategy.strategic_objectives(id, workspace_id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.okr_objectives ADD CONSTRAINT fk_okr_objectives_tows_option FOREIGN KEY (tows_option_id, workspace_id) REFERENCES strategy.tows_options(id, workspace_id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.pestel_signals ADD CONSTRAINT fk_pestel_signals_objective FOREIGN KEY (strategic_objective_id, workspace_id) REFERENCES strategy.strategic_objectives(id, workspace_id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.portfolio_projects ADD CONSTRAINT fk_portfolio_projects_portfolio_ws FOREIGN KEY (portfolio_id, workspace_id) REFERENCES strategy.portfolios(id, workspace_id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.portfolio_projects ADD CONSTRAINT fk_portfolio_projects_project_ws FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.resource_capability_assessments ADD CONSTRAINT fk_resource_assessments_objective FOREIGN KEY (strategic_objective_id, workspace_id) REFERENCES strategy.strategic_objectives(id, workspace_id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.strategic_objectives ADD CONSTRAINT fk_strategic_objectives_project FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.swot_items ADD CONSTRAINT fk_swot_items_objective FOREIGN KEY (strategic_objective_id, workspace_id) REFERENCES strategy.strategic_objectives(id, workspace_id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.tows_options ADD CONSTRAINT fk_tows_options_objective FOREIGN KEY (strategic_objective_id, workspace_id) REFERENCES strategy.strategic_objectives(id, workspace_id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.gate_evaluations ADD CONSTRAINT gate_evaluations_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.gate_evaluations ADD CONSTRAINT gate_evaluations_stage_policy_id_fkey FOREIGN KEY (stage_policy_id) REFERENCES strategy.stage_policies(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.initiative_key_results ADD CONSTRAINT initiative_key_results_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.initiatives ADD CONSTRAINT initiatives_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES strategy.decision_records(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.key_results ADD CONSTRAINT key_results_objective_id_fkey FOREIGN KEY (objective_id) REFERENCES strategy.okr_objectives(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.maturity_assessments ADD CONSTRAINT maturity_assessments_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.maturity_assessments ADD CONSTRAINT maturity_assessments_scoreboard_run_id_fkey FOREIGN KEY (scoreboard_run_id) REFERENCES strategy.pmf_scoreboard_runs(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.metric_contracts ADD CONSTRAINT metric_contracts_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.metric_snapshots ADD CONSTRAINT metric_snapshots_contract_version_id_fkey FOREIGN KEY (contract_version_id) REFERENCES strategy.metric_contracts(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.metric_snapshots ADD CONSTRAINT metric_snapshots_evidence_ingestion_id_fkey FOREIGN KEY (evidence_ingestion_id) REFERENCES strategy.evidence_ingestions(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.metric_snapshots ADD CONSTRAINT metric_snapshots_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.next_action_candidates ADD CONSTRAINT next_action_candidates_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.next_action_rankings ADD CONSTRAINT next_action_rankings_candidate_id_fkey FOREIGN KEY (candidate_id) REFERENCES strategy.next_action_candidates(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.next_action_rankings ADD CONSTRAINT next_action_rankings_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.next_best_actions ADD CONSTRAINT next_best_actions_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES strategy.decision_records(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.next_best_actions ADD CONSTRAINT next_best_actions_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.okr_objectives ADD CONSTRAINT okr_objectives_cycle_id_fkey FOREIGN KEY (cycle_id) REFERENCES strategy.okr_cycles(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.pestel_signals ADD CONSTRAINT pestel_signals_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.pilot_runs ADD CONSTRAINT pilot_runs_experiment_id_fkey FOREIGN KEY (experiment_id) REFERENCES strategy.experiments(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.pilot_runs ADD CONSTRAINT pilot_runs_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.pmf_scoreboard_runs ADD CONSTRAINT pmf_scoreboard_runs_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.portfolio_projects ADD CONSTRAINT portfolio_projects_portfolio_id_fkey FOREIGN KEY (portfolio_id) REFERENCES strategy.portfolios(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.portfolio_projects ADD CONSTRAINT portfolio_projects_project_id_fkey FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.resource_capability_assessments ADD CONSTRAINT resource_capability_assessments_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.stage_transition_policies ADD CONSTRAINT stage_transitions_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES strategy.stage_policies(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.strategic_objectives ADD CONSTRAINT strategic_objectives_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.swot_items ADD CONSTRAINT swot_items_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.tows_option_evaluations ADD CONSTRAINT tows_option_evaluations_tows_option_id_fkey FOREIGN KEY (tows_option_id) REFERENCES strategy.tows_options(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.tows_option_evaluations ADD CONSTRAINT tows_option_evaluations_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.tows_options ADD CONSTRAINT tows_options_decision_id_fkey FOREIGN KEY (decision_id) REFERENCES strategy.decision_records(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.tows_options ADD CONSTRAINT tows_options_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;

-- ---- FK ngược chiều: bảng con ở `001`/`004`, bảng cha ở `005` ----
DO $$ BEGIN ALTER TABLE operating.tasks ADD CONSTRAINT fk_tasks_initiative_id FOREIGN KEY (initiative_id) REFERENCES strategy.initiatives(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE operating.weekly_commitments ADD CONSTRAINT weekly_commitments_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES strategy.initiatives(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.decision_records ADD CONSTRAINT decision_records_gate_evaluation_id_fkey FOREIGN KEY (gate_evaluation_id) REFERENCES strategy.gate_evaluations(id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.okr_objective_projects ADD CONSTRAINT fk_okr_objective_projects_objective FOREIGN KEY (objective_id, workspace_id) REFERENCES strategy.okr_objectives(id, workspace_id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE strategy.projects ADD CONSTRAINT fk_projects_portfolio_ws FOREIGN KEY (portfolio_id, workspace_id) REFERENCES strategy.portfolios(id, workspace_id) ON DELETE SET NULL (portfolio_id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; END $$;
