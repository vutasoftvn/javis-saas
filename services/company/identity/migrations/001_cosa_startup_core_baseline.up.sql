-- COSA Startup Core baseline migration for services/company/identity

-- GENERATED from a pg_dump --schema-only of the fully-migrated dev DB,
-- then filtered to the Founder Trial R1 retained allowlist. Review before use.
-- Task 10 of docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS integration;

CREATE TABLE IF NOT EXISTS core.cosa_delegation_replays (
    jti text NOT NULL,
    capability_id text NOT NULL,
    workspace_id text NOT NULL,
    run_id text NOT NULL,
    consumed_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY core.cosa_delegation_replays ADD CONSTRAINT cosa_delegation_replays_pkey PRIMARY KEY (jti, capability_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS cosa_delegation_replays_workspace_run_idx ON core.cosa_delegation_replays USING btree (workspace_id, run_id);


CREATE TABLE IF NOT EXISTS core.user_projections (
    id bigint NOT NULL,
    email text,
    phone text,
    display_name text,
    status text DEFAULT 'active'::text NOT NULL,
    platform_user_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT user_projections_email_or_phone_required CHECK (((email IS NOT NULL) OR (phone IS NOT NULL)))
);

DO $$ BEGIN
  ALTER TABLE ONLY core.user_projections ADD CONSTRAINT user_projections_email_key UNIQUE (email);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.user_projections ADD CONSTRAINT user_projections_phone_key UNIQUE (phone);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.user_projections ADD CONSTRAINT user_projections_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.user_projections ADD CONSTRAINT user_projections_platform_user_id_key UNIQUE (platform_user_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS core.workspaces (
    id bigint NOT NULL,
    name text NOT NULL,
    lifecycle_stage text DEFAULT 'W0_IDEA'::text NOT NULL,
    platform_company_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    platform_workspace_id text,
    stage_entered_at timestamp with time zone,
    slug text,
    status text DEFAULT 'ACTIVE'::text NOT NULL,
    stage_version integer DEFAULT 0 NOT NULL,
    runtime_mode text DEFAULT 'LOCAL_ONLY'::text NOT NULL,
    sync_policy text DEFAULT 'CONTROL_METADATA_ONLY'::text NOT NULL,
    sync_status text DEFAULT 'LOCAL_ONLY'::text NOT NULL,
    primary_legal_entity_id bigint,
    archived_at timestamp with time zone,
    vision text,
    mission text,
    core_values text,
    CONSTRAINT workspaces_lifecycle_stage_chk CHECK ((lifecycle_stage = ANY (ARRAY['W0_IDEA'::text, 'W1_PROBLEM_VALIDATION'::text, 'W2_SOLUTION_VALIDATION'::text, 'W3_MVP_BUILD'::text, 'W4_PRODUCT_MARKET_FIT'::text, 'W5_SCALE'::text]))),
    CONSTRAINT workspaces_runtime_mode_chk CHECK ((runtime_mode = ANY (ARRAY['LOCAL_ONLY'::text, 'REMOTE_ACCESS'::text, 'CLOUD_CONTINUITY'::text]))),
    CONSTRAINT workspaces_status_chk CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'ARCHIVED'::text, 'SUSPENDED'::text]))),
    CONSTRAINT workspaces_sync_policy_chk CHECK ((sync_policy = ANY (ARRAY['CONTROL_METADATA_ONLY'::text, 'SELECTIVE_ENCRYPTED'::text, 'FULL_ENCRYPTED'::text]))),
    CONSTRAINT workspaces_sync_status_chk CHECK ((sync_status = ANY (ARRAY['LOCAL_ONLY'::text, 'PENDING'::text, 'IN_SYNC'::text, 'CONFLICT'::text, 'ERROR'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY core.workspaces ADD CONSTRAINT workspaces_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.workspaces ADD CONSTRAINT workspaces_platform_company_id_key UNIQUE (platform_company_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.workspaces ADD CONSTRAINT workspaces_platform_workspace_id_key UNIQUE (platform_workspace_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_workspaces_slug ON core.workspaces USING btree (slug) WHERE (slug IS NOT NULL);


CREATE TABLE IF NOT EXISTS core.workforce_members (
    id bigint NOT NULL,
    member_type text NOT NULL,
    human_user_id bigint,
    role_title text NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    workspace_id bigint NOT NULL,
    agent_spec_id text,
    agent_spec_version text,
    manager_member_id bigint,
    CONSTRAINT workforce_members_manager_not_self CHECK (((manager_member_id IS NULL) OR (manager_member_id <> id))),
    CONSTRAINT workforce_members_type_consistency CHECK ((((member_type = 'HUMAN'::text) AND (human_user_id IS NOT NULL) AND (agent_spec_id IS NULL) AND (agent_spec_version IS NULL)) OR ((member_type = 'AI_AGENT'::text) AND (human_user_id IS NULL) AND (agent_spec_id IS NOT NULL) AND (agent_spec_version IS NOT NULL))))
);

DO $$ BEGIN
  ALTER TABLE ONLY core.workforce_members ADD CONSTRAINT uq_workforce_members_id_workspace UNIQUE (id, workspace_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.workforce_members ADD CONSTRAINT workforce_members_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.workforce_members ADD CONSTRAINT workforce_members_human_user_id_fkey FOREIGN KEY (human_user_id) REFERENCES core.user_projections(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.workforce_members ADD CONSTRAINT workforce_members_manager_same_workspace_fkey FOREIGN KEY (manager_member_id, workspace_id) REFERENCES core.workforce_members(id, workspace_id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.workforce_members ADD CONSTRAINT workforce_members_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_workforce_members_human_user_id ON core.workforce_members USING btree (human_user_id);


CREATE TABLE IF NOT EXISTS core.workspace_roles (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workspace_id bigint NOT NULL,
    role_key text NOT NULL,
    name text NOT NULL,
    is_system boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY core.workspace_roles ADD CONSTRAINT uq_workspace_roles_key UNIQUE (workspace_id, role_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.workspace_roles ADD CONSTRAINT workspace_roles_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.workspace_roles ADD CONSTRAINT workspace_roles_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS core.member_role_assignments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    workspace_id bigint NOT NULL,
    workforce_member_id bigint NOT NULL,
    role_id uuid NOT NULL,
    project_id bigint,
    legal_entity_id bigint,
    valid_from timestamp with time zone DEFAULT now() NOT NULL,
    valid_until timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT check_valid_until_after_valid_from CHECK (((valid_until IS NULL) OR (valid_until > valid_from)))
);

DO $$ BEGIN
  ALTER TABLE ONLY core.member_role_assignments ADD CONSTRAINT member_role_assignments_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.member_role_assignments ADD CONSTRAINT member_role_assignments_role_id_fkey FOREIGN KEY (role_id) REFERENCES core.workspace_roles(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.member_role_assignments ADD CONSTRAINT member_role_assignments_workforce_member_id_fkey FOREIGN KEY (workforce_member_id) REFERENCES core.workforce_members(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.member_role_assignments ADD CONSTRAINT member_role_assignments_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_member_role_assignments_lookup ON core.member_role_assignments USING btree (workspace_id, workforce_member_id);


CREATE TABLE IF NOT EXISTS core.permission_definitions (
    permission_key text NOT NULL,
    domain text NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY core.permission_definitions ADD CONSTRAINT permission_definitions_pkey PRIMARY KEY (permission_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS core.role_permissions (
    role_id uuid NOT NULL,
    permission_key text NOT NULL,
    effect text NOT NULL,
    conditions jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT role_permissions_effect_check CHECK ((effect = ANY (ARRAY['ALLOW'::text, 'DENY'::text, 'REQUIRE_APPROVAL'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY core.role_permissions ADD CONSTRAINT role_permissions_pkey PRIMARY KEY (role_id, permission_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.role_permissions ADD CONSTRAINT role_permissions_permission_key_fkey FOREIGN KEY (permission_key) REFERENCES core.permission_definitions(permission_key) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.role_permissions ADD CONSTRAINT role_permissions_role_id_fkey FOREIGN KEY (role_id) REFERENCES core.workspace_roles(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS core.workspace_memberships (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    user_id bigint NOT NULL,
    role text DEFAULT 'member'::text NOT NULL,
    platform_membership_id text,
    source_updated_at timestamp with time zone,
    synced_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

DO $$ BEGIN
  ALTER TABLE ONLY core.workspace_memberships ADD CONSTRAINT workspace_memberships_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.workspace_memberships ADD CONSTRAINT workspace_memberships_workspace_id_user_id_key UNIQUE (workspace_id, user_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.workspace_memberships ADD CONSTRAINT workspace_memberships_user_id_fkey FOREIGN KEY (user_id) REFERENCES core.user_projections(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.workspace_memberships ADD CONSTRAINT workspace_memberships_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_workspace_memberships_user_id ON core.workspace_memberships USING btree (user_id);

CREATE INDEX IF NOT EXISTS idx_workspace_memberships_workspace_id ON core.workspace_memberships USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS core.workspace_slugs (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    slug text NOT NULL,
    status text DEFAULT 'ACTIVE'::text NOT NULL,
    redirect_to_slug text,
    reserved_at timestamp with time zone DEFAULT now() NOT NULL,
    released_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT workspace_slugs_status_check CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'REDIRECT'::text, 'RELEASED'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY core.workspace_slugs ADD CONSTRAINT workspace_slugs_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY core.workspace_slugs ADD CONSTRAINT workspace_slugs_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_workspace_slugs_workspace ON core.workspace_slugs USING btree (workspace_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_workspace_slugs_active ON core.workspace_slugs USING btree (slug) WHERE (status = ANY (ARRAY['ACTIVE'::text, 'REDIRECT'::text]));

CREATE UNIQUE INDEX IF NOT EXISTS uq_workspace_slugs_one_active_per_workspace ON core.workspace_slugs USING btree (workspace_id) WHERE (status = 'ACTIVE'::text);


CREATE TABLE IF NOT EXISTS integration.event_audit (
    id bigint NOT NULL,
    workspace_id text NOT NULL,
    action text NOT NULL,
    payload jsonb NOT NULL,
    actor_id text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY integration.event_audit ADD CONSTRAINT event_audit_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_event_audit_ws_action ON integration.event_audit USING btree (workspace_id, action, created_at DESC);


CREATE TABLE IF NOT EXISTS integration.event_outbox (
    id bigint NOT NULL,
    event_id uuid NOT NULL,
    workspace_id text NOT NULL,
    aggregate_type text NOT NULL,
    aggregate_id text NOT NULL,
    event_type text NOT NULL,
    schema_version integer NOT NULL,
    occurred_at timestamp with time zone NOT NULL,
    envelope jsonb NOT NULL,
    payload_hash text NOT NULL,
    classification text NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    max_attempts integer DEFAULT 8 NOT NULL,
    claim_token text,
    visibility_timeout_at timestamp with time zone,
    last_error text,
    dead_letter_reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    delivered_at timestamp with time zone,
    CONSTRAINT event_outbox_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'claimed'::text, 'delivered'::text, 'dead'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY integration.event_outbox ADD CONSTRAINT event_outbox_event_id_key UNIQUE (event_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY integration.event_outbox ADD CONSTRAINT event_outbox_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_event_outbox_due ON integration.event_outbox USING btree (visibility_timeout_at) WHERE (status = ANY (ARRAY['pending'::text, 'claimed'::text]));

CREATE INDEX IF NOT EXISTS idx_event_outbox_type ON integration.event_outbox USING btree (event_type);

CREATE INDEX IF NOT EXISTS idx_event_outbox_ws_aggr ON integration.event_outbox USING btree (workspace_id, aggregate_type, aggregate_id);



-- Fix gaps in 001_founder_trial_mvp_baseline (a pg_dump --schema-only squash
-- that lost several objects the running code still depends on):
--
--  1. core.workspace_policy_versions + core.business_policy_cutover_markers were
--     dropped, but services/company/identity's tenant-context / business-policy
--     resolver queries workspace_policy_versions on every /operations/* request.
--  2. integration.event_outbox.id and integration.event_audit.id lost their
--     `GENERATED ALWAYS AS IDENTITY` clause (pg_dump splits it into a separate
--     ALTER that the squash filtered out). The Drizzle schema declares
--     `.generatedAlwaysAsIdentity()`, so INSERTs omit `id` and the DB must fill
--     it — without identity they fail the NOT NULL constraint.
--
-- Expand-only, idempotent.

CREATE TABLE IF NOT EXISTS core.workspace_policy_versions (
  workspace_id      BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  version           INTEGER NOT NULL,
  policy_hash       TEXT NOT NULL,
  actor_member_id   BIGINT,
  reason            TEXT,
  source            TEXT NOT NULL DEFAULT 'native',
  cutover_at        TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (workspace_id, version)
);

CREATE TABLE IF NOT EXISTS core.business_policy_cutover_markers (
  workspace_id          BIGINT PRIMARY KEY REFERENCES core.workspaces(id) ON DELETE CASCADE,
  cutover_completed     BOOLEAN NOT NULL DEFAULT false,
  cutover_at            TIMESTAMPTZ,
  migrated_rule_count   INTEGER NOT NULL DEFAULT 0,
  needs_review_count    INTEGER NOT NULL DEFAULT 0,
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Re-attach the identity clause only where it is missing (attidentity = '' means
-- not an identity column). Safe on a fresh baseline DB (no rows) and a no-op on
-- a DB migrated the pre-squash way (already identity).
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'integration' AND c.relname = 'event_outbox'
      AND a.attname = 'id' AND a.attidentity = '' AND NOT a.atthasdef
  ) THEN
    EXECUTE 'ALTER TABLE integration.event_outbox ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY';
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'integration' AND c.relname = 'event_audit'
      AND a.attname = 'id' AND a.attidentity = '' AND NOT a.atthasdef
  ) THEN
    EXECUTE 'ALTER TABLE integration.event_audit ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY';
  END IF;
END $$;
