-- COSA Startup Core — 002: reconcile 001 baseline with the trimmed Drizzle
-- schema (drizzle-kit generate). Adds retained tables/columns the curated
-- 001 omitted. Framework tables were already removed from the schema, so
-- none are (re)introduced here. Expand-only + idempotent.

CREATE TABLE IF NOT EXISTS "operating"."automation_definitions" (

  "id" bigint PRIMARY KEY NOT NULL,
  "workspace_id" bigint NOT NULL,
  "automation_key" text NOT NULL,
  "current_revision_id" bigint,
  "lifecycle_state" text DEFAULT 'DRAFT' NOT NULL,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL,
  "updated_at" timestamp with time zone DEFAULT now() NOT NULL,
  "deleted_at" timestamp with time zone
);
CREATE TABLE IF NOT EXISTS "operating"."automation_invocation_events" (

  "id" bigint PRIMARY KEY NOT NULL,
  "workspace_id" bigint NOT NULL,
  "invocation_id" bigint NOT NULL,
  "seq" integer NOT NULL,
  "event_type" text NOT NULL,
  "payload_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL
);
CREATE TABLE IF NOT EXISTS "operating"."automation_invocations" (

  "id" bigint PRIMARY KEY NOT NULL,
  "workspace_id" bigint NOT NULL,
  "definition_id" bigint NOT NULL,
  "revision_id" bigint NOT NULL,
  "automation_key" text NOT NULL,
  "revision_no" integer NOT NULL,
  "revision_hash" text NOT NULL,
  "idempotency_key" text NOT NULL,
  "trigger_kind" text NOT NULL,
  "trigger_identity" text NOT NULL,
  "caller_principal" text NOT NULL,
  "source" text NOT NULL,
  "business_scope_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
  "validated_input_ref" text,
  "fingerprint_hash" text NOT NULL,
  "state" text DEFAULT 'REQUESTED' NOT NULL,
  "blocked_reason" text,
  "agent_run_id" text,
  "correlation_id" text NOT NULL,
  "version" integer DEFAULT 1 NOT NULL,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL,
  "updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
CREATE TABLE IF NOT EXISTS "operating"."automation_revisions" (

  "id" bigint PRIMARY KEY NOT NULL,
  "workspace_id" bigint NOT NULL,
  "definition_id" bigint NOT NULL,
  "revision_no" integer NOT NULL,
  "revision_hash" text NOT NULL,
  "configuration_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
  "trigger_contract_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
  "capability_ids" jsonb DEFAULT '[]'::jsonb NOT NULL,
  "evidence_contract_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
  "autonomy_class" text DEFAULT 'read_only' NOT NULL,
  "approval_contract_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
  "pinned_dependencies_json" jsonb DEFAULT '{}'::jsonb NOT NULL,
  "effective_policy_revision" text,
  "created_by" text NOT NULL,
  "published_at" timestamp with time zone,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL
);
CREATE TABLE IF NOT EXISTS "strategy"."discovery_signals" (

  "id" bigint PRIMARY KEY NOT NULL,
  "workspace_id" bigint NOT NULL,
  "project_id" bigint NOT NULL,
  "signal_type" varchar(50) NOT NULL,
  "payload" jsonb DEFAULT '{}'::jsonb NOT NULL,
  "source" text NOT NULL,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL,
  "updated_at" timestamp with time zone DEFAULT now() NOT NULL,
  "deleted_at" timestamp with time zone
);
CREATE TABLE IF NOT EXISTS "strategy"."initiative_key_results" (

  "workspace_id" bigint NOT NULL,
  "initiative_id" bigint NOT NULL,
  "key_result_id" bigint NOT NULL,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL,
  CONSTRAINT "initiative_key_results_workspace_id_initiative_id_key_result_id_pk" PRIMARY KEY("workspace_id","initiative_id","key_result_id")
);
CREATE TABLE IF NOT EXISTS "strategy"."metric_contracts" (

  "id" bigint PRIMARY KEY NOT NULL,
  "workspace_id" bigint NOT NULL,
  "project_id" bigint NOT NULL,
  "metric_key" varchar(100) NOT NULL,
  "display_name" text NOT NULL,
  "unit" varchar(50) NOT NULL,
  "numerator_definition" text NOT NULL,
  "denominator_definition" text NOT NULL,
  "cohort_definition" text NOT NULL,
  "source_mapping" jsonb DEFAULT '{}'::jsonb NOT NULL,
  "cadence" varchar(50) NOT NULL,
  "fresh_until" timestamp with time zone,
  "guardrail" text,
  "owner_member_id" bigint,
  "decision_use" text NOT NULL,
  "status" varchar(50) DEFAULT 'DRAFT' NOT NULL,
  "version" integer DEFAULT 1 NOT NULL,
  "approval_ref" text,
  "change_rationale" text,
  "created_by_member_id" bigint,
  "published_by_member_id" bigint,
  "published_at" timestamp with time zone,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL,
  "updated_at" timestamp with time zone DEFAULT now() NOT NULL,
  "deleted_at" timestamp with time zone
);
CREATE TABLE IF NOT EXISTS "strategy"."metric_snapshots" (

  "id" bigint PRIMARY KEY NOT NULL,
  "workspace_id" bigint NOT NULL,
  "project_id" bigint NOT NULL,
  "contract_version_id" bigint NOT NULL,
  "source_system" varchar(50) NOT NULL,
  "source_window" varchar(50) NOT NULL,
  "source_record_id" text NOT NULL,
  "payload_hash" text NOT NULL,
  "observed_at" timestamp with time zone NOT NULL,
  "captured_at" timestamp with time zone DEFAULT now() NOT NULL,
  "value" double precision NOT NULL,
  "numerator" double precision,
  "denominator" double precision,
  "quality_status" varchar(30) DEFAULT 'VALID' NOT NULL,
  "quality_checks" jsonb DEFAULT '{}'::jsonb NOT NULL,
  "evidence_ingestion_id" bigint,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL
);
CREATE TABLE IF NOT EXISTS "strategy"."next_best_actions" (

  "id" bigint PRIMARY KEY NOT NULL,
  "workspace_id" bigint NOT NULL,
  "source" text NOT NULL,
  "project_id" bigint,
  "decision_id" bigint,
  "recommendation" text NOT NULL,
  "priority" integer DEFAULT 1 NOT NULL,
  "due_by" date,
  "status" text DEFAULT 'PROPOSED' NOT NULL,
  "revision" integer DEFAULT 1 NOT NULL,
  "capability_required" text,
  "decision_reason" text NOT NULL,
  "context_snapshot" jsonb DEFAULT '{}'::jsonb NOT NULL,
  "evidence_refs" jsonb DEFAULT '[]'::jsonb NOT NULL,
  "regulation_refs" jsonb DEFAULT '[]'::jsonb NOT NULL,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL,
  "updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
CREATE TABLE IF NOT EXISTS "strategy"."okr_cycles" (

  "id" bigint PRIMARY KEY NOT NULL,
  "workspace_id" bigint NOT NULL,
  "name" text NOT NULL,
  "start_date" timestamp with time zone,
  "end_date" timestamp with time zone,
  "status" text DEFAULT 'draft' NOT NULL,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL,
  "updated_at" timestamp with time zone DEFAULT now() NOT NULL,
  "deleted_at" timestamp with time zone
);
CREATE TABLE IF NOT EXISTS "strategy"."pilot_runs" (

  "id" bigint PRIMARY KEY NOT NULL,
  "workspace_id" bigint NOT NULL,
  "project_id" bigint NOT NULL,
  "experiment_id" bigint,
  "status" varchar(50) DEFAULT 'DRAFT' NOT NULL,
  "design_partner_evidence_refs" jsonb DEFAULT '[]'::jsonb NOT NULL,
  "metric_contract_artifact_ref" text,
  "instrumentation_artifact_ref" text,
  "onboarding_artifact_ref" text,
  "support_escalation_artifact_ref" text,
  "rollback_artifact_ref" text,
  "release_owner_member_id" bigint NOT NULL,
  "approved_by_member_id" bigint,
  "approval_ref" text,
  "approved_at" timestamp with time zone,
  "activated_by_member_id" bigint,
  "activated_at" timestamp with time zone,
  "completed_at" timestamp with time zone,
  "cancelled_at" timestamp with time zone,
  "cancellation_reason" text,
  "version" integer DEFAULT 1 NOT NULL,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL,
  "updated_at" timestamp with time zone DEFAULT now() NOT NULL,
  "deleted_at" timestamp with time zone
);
CREATE TABLE IF NOT EXISTS "strategy"."venture_profiles" (

  "id" bigint PRIMARY KEY NOT NULL,
  "workspace_id" bigint NOT NULL,
  "problem_statement" text,
  "target_customer" text,
  "industry" text,
  "geography" text,
  "currency" text DEFAULT 'VND',
  "timezone" text DEFAULT 'Asia/Ho_Chi_Minh',
  "founder_goal" varchar(50),
  "initial_runway_months" integer,
  "stage_entered_at" timestamp with time zone,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL,
  "updated_at" timestamp with time zone DEFAULT now() NOT NULL,
  CONSTRAINT "venture_profiles_workspace_id_unique" UNIQUE("workspace_id")
);
CREATE TABLE IF NOT EXISTS "strategy"."weekly_reviews" (

  "id" bigint PRIMARY KEY NOT NULL,
  "workspace_id" bigint NOT NULL,
  "week_start_date" date NOT NULL,
  "summary" text NOT NULL,
  "stage_assessment" text,
  "cash_summary" text,
  "obligations_summary" text,
  "action_proposals" jsonb DEFAULT '[]'::jsonb NOT NULL,
  "weekly_plan_ids" jsonb DEFAULT '[]'::jsonb NOT NULL,
  "decision_ids" jsonb DEFAULT '[]'::jsonb NOT NULL,
  "status" text DEFAULT 'DRAFT' NOT NULL,
  "revision" integer DEFAULT 1 NOT NULL,
  "created_at" timestamp with time zone DEFAULT now() NOT NULL,
  "updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
