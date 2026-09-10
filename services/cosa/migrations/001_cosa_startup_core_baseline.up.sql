-- COSA Startup Core baseline migration for services/cosa

-- GENERATED from a pg_dump --schema-only of the fully-migrated dev DB,
-- then filtered to the Founder Trial R1 retained allowlist. Review before use.
-- Task 10 of docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md

CREATE SCHEMA IF NOT EXISTS control_plane;
CREATE SCHEMA IF NOT EXISTS cosa;

CREATE TABLE IF NOT EXISTS control_plane.workspace_connector_installations (
    id text NOT NULL,
    workspace_id text NOT NULL,
    connector_key text NOT NULL,
    installed_by text NOT NULL,
    status text DEFAULT 'enabled'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_installation_status CHECK ((status = ANY (ARRAY['enabled'::text, 'disabled'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.workspace_connector_installations ADD CONSTRAINT uq_connector_installation UNIQUE (workspace_id, connector_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.workspace_connector_installations ADD CONSTRAINT workspace_connector_installations_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS control_plane.connector_authorizations (
    id text NOT NULL,
    installation_id text NOT NULL,
    principal_id text NOT NULL,
    secret_ref text NOT NULL,
    granted_scopes jsonb DEFAULT '[]'::jsonb NOT NULL,
    state text DEFAULT 'active'::text NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    workspace_id text NOT NULL,
    CONSTRAINT chk_authorization_state CHECK ((state = ANY (ARRAY['active'::text, 'expired'::text, 'revoked'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.connector_authorizations ADD CONSTRAINT connector_authorizations_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.connector_authorizations ADD CONSTRAINT connector_authorizations_installation_id_fkey FOREIGN KEY (installation_id) REFERENCES control_plane.workspace_connector_installations(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_connector_authorizations_workspace ON control_plane.connector_authorizations USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS control_plane.session_connector_grants (
    id text NOT NULL,
    workspace_id text NOT NULL,
    conversation_id text NOT NULL,
    authorization_id text NOT NULL,
    granted_by text NOT NULL,
    allowed_actions jsonb DEFAULT '[]'::jsonb NOT NULL,
    state text DEFAULT 'enabled'::text NOT NULL,
    expires_at timestamp with time zone,
    revoked_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_session_grant_state CHECK ((state = ANY (ARRAY['enabled'::text, 'revoked'::text, 'expired'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.session_connector_grants ADD CONSTRAINT session_connector_grants_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.session_connector_grants ADD CONSTRAINT uq_session_grant UNIQUE (conversation_id, authorization_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.session_connector_grants ADD CONSTRAINT session_connector_grants_authorization_id_fkey FOREIGN KEY (authorization_id) REFERENCES control_plane.connector_authorizations(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS control_plane.snowflake_generator_slots (
    generator_id text NOT NULL,
    slot integer NOT NULL,
    runtime_role text NOT NULL,
    lease_epoch bigint DEFAULT 1 NOT NULL,
    fencing_token bigint NOT NULL,
    lease_expires_at timestamp with time zone NOT NULL,
    last_heartbeat_at timestamp with time zone DEFAULT now() NOT NULL,
    clock_checkpoint bigint DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT snowflake_generator_slots_runtime_role_check CHECK ((runtime_role = ANY (ARRAY['cosa_control_plane'::text, 'cloud_workspace_runtime'::text]))),
    CONSTRAINT snowflake_generator_slots_slot_check CHECK (((slot >= 0) AND (slot <= 1023)))
);

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.snowflake_generator_slots ADD CONSTRAINT snowflake_generator_slots_pkey PRIMARY KEY (generator_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_snowflake_generator_slot ON control_plane.snowflake_generator_slots USING btree (slot);


CREATE TABLE IF NOT EXISTS control_plane.workspace_runtime_nodes (
    node_id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    device_key_fingerprint text NOT NULL,
    runtime_role text NOT NULL,
    presence_status text DEFAULT 'OFFLINE'::text NOT NULL,
    agent_version text,
    last_heartbeat_at timestamp with time zone,
    registered_at timestamp with time zone DEFAULT now() NOT NULL,
    revoked_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT workspace_runtime_nodes_presence_status_check CHECK ((presence_status = ANY (ARRAY['ONLINE'::text, 'OFFLINE'::text, 'DEGRADED'::text]))),
    CONSTRAINT workspace_runtime_nodes_runtime_role_check CHECK ((runtime_role = ANY (ARRAY['local_workspace_runtime'::text, 'cloud_workspace_runtime'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.workspace_runtime_nodes ADD CONSTRAINT workspace_runtime_nodes_pkey PRIMARY KEY (node_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_workspace_runtime_nodes_ws_presence ON control_plane.workspace_runtime_nodes USING btree (workspace_id, presence_status);

CREATE UNIQUE INDEX IF NOT EXISTS uq_workspace_runtime_nodes_ws_fingerprint ON control_plane.workspace_runtime_nodes USING btree (workspace_id, device_key_fingerprint) WHERE (revoked_at IS NULL);


CREATE TABLE IF NOT EXISTS control_plane.workspace_schedule_definitions (
    id text NOT NULL,
    workspace_id text NOT NULL,
    created_by text NOT NULL,
    schedule_kind text NOT NULL,
    timezone text DEFAULT 'Asia/Ho_Chi_Minh'::text NOT NULL,
    run_at timestamp with time zone,
    hour integer,
    minute integer,
    weekdays jsonb DEFAULT '[]'::jsonb NOT NULL,
    prompt_template text NOT NULL,
    agent_profile text DEFAULT 'operations'::text NOT NULL,
    connector_grant_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    state text DEFAULT 'enabled'::text NOT NULL,
    next_run_at timestamp with time zone,
    last_run_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_schedule_kind CHECK ((schedule_kind = ANY (ARRAY['one_time'::text, 'daily'::text, 'weekdays'::text]))),
    CONSTRAINT chk_schedule_state CHECK ((state = ANY (ARRAY['enabled'::text, 'paused'::text, 'archived'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.workspace_schedule_definitions ADD CONSTRAINT workspace_schedule_definitions_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_workspace_schedules_due ON control_plane.workspace_schedule_definitions USING btree (state, next_run_at);


CREATE TABLE IF NOT EXISTS control_plane.workspace_schedule_executions (
    id text NOT NULL,
    definition_id text NOT NULL,
    workspace_id text NOT NULL,
    scheduled_for timestamp with time zone NOT NULL,
    prompt_template_snapshot text NOT NULL,
    agent_profile_snapshot text NOT NULL,
    connector_grant_ids_snapshot jsonb DEFAULT '[]'::jsonb NOT NULL,
    state text DEFAULT 'queued'::text NOT NULL,
    task_id text,
    conversation_id text,
    run_id text,
    error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    next_attempt_at timestamp with time zone,
    CONSTRAINT chk_schedule_execution_state CHECK ((state = ANY (ARRAY['queued'::text, 'enqueue_retry'::text, 'enqueue_failed'::text, 'running'::text, 'succeeded'::text, 'failed'::text, 'blocked_reauth'::text, 'cancelled'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.workspace_schedule_executions ADD CONSTRAINT uq_schedule_execution UNIQUE (definition_id, scheduled_for);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.workspace_schedule_executions ADD CONSTRAINT workspace_schedule_executions_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.workspace_schedule_executions ADD CONSTRAINT workspace_schedule_executions_definition_id_fkey FOREIGN KEY (definition_id) REFERENCES control_plane.workspace_schedule_definitions(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS control_plane.workspace_settings_audit_events (
    event_id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    actor_id text NOT NULL,
    event_type text NOT NULL,
    target_kind text NOT NULL,
    target_id text NOT NULL,
    details jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.workspace_settings_audit_events ADD CONSTRAINT workspace_settings_audit_events_pkey PRIMARY KEY (event_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_workspace_settings_audit_events_ws ON control_plane.workspace_settings_audit_events USING btree (workspace_id, created_at DESC);


CREATE TABLE IF NOT EXISTS control_plane.workspace_skill_policies (
    workspace_id bigint NOT NULL,
    skill_key text NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    revision integer DEFAULT 1 NOT NULL,
    updated_by text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY control_plane.workspace_skill_policies ADD CONSTRAINT workspace_skill_policies_pkey PRIMARY KEY (workspace_id, skill_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_workspace_skill_policies_ws_updated ON control_plane.workspace_skill_policies USING btree (workspace_id, updated_at DESC);


CREATE TABLE IF NOT EXISTS cosa.plans (
    id text NOT NULL,
    name text NOT NULL,
    description text,
    default_limits jsonb DEFAULT '{"max_seats": 2, "max_projects": 1, "max_scheduled_agents": 1}'::jsonb NOT NULL,
    default_features jsonb DEFAULT '{"crm": true, "finance": false, "marketing": true, "custom_domain": false}'::jsonb NOT NULL,
    is_public boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.plans ADD CONSTRAINT plans_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS cosa.roles (
    id text NOT NULL,
    scope text,
    level integer,
    description text,
    name text DEFAULT 'Legacy role'::text NOT NULL,
    category text DEFAULT 'legacy'::text NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.roles ADD CONSTRAINT roles_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS cosa.users (
    id bigint NOT NULL,
    email text,
    phone text,
    hashed_password text NOT NULL,
    is_platform_admin boolean DEFAULT false NOT NULL,
    platform_role_id text,
    status text DEFAULT 'active'::text NOT NULL,
    last_login_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT users_email_or_phone_required CHECK (((email IS NOT NULL) OR (phone IS NOT NULL)))
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.users ADD CONSTRAINT users_email_key UNIQUE (email);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.users ADD CONSTRAINT users_phone_key UNIQUE (phone);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.users ADD CONSTRAINT users_platform_role_id_fkey FOREIGN KEY (platform_role_id) REFERENCES cosa.roles(id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_cp_users_email ON cosa.users USING btree (email);

CREATE INDEX IF NOT EXISTS idx_cp_users_phone ON cosa.users USING btree (phone);


CREATE TABLE IF NOT EXISTS cosa.profiles (
    user_id bigint NOT NULL,
    full_name text,
    avatar_url text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    role_id text DEFAULT 'member'::text NOT NULL,
    bio text,
    headline text,
    preferred_locale character varying(10) DEFAULT 'vi-VN'::character varying NOT NULL,
    CONSTRAINT chk_profiles_preferred_locale CHECK (((preferred_locale)::text = ANY ((ARRAY['vi-VN'::character varying, 'en-US'::character varying])::text[])))
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.profiles ADD CONSTRAINT profiles_pkey PRIMARY KEY (user_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.profiles ADD CONSTRAINT profiles_role_id_fkey FOREIGN KEY (role_id) REFERENCES cosa.roles(id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.profiles ADD CONSTRAINT profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES cosa.users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS cosa.workspaces (
    id bigint NOT NULL,
    workspace_name text NOT NULL,
    owner_user_id bigint NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT platform_workspaces_status_check CHECK ((status = ANY (ARRAY['active'::text, 'archived'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspaces ADD CONSTRAINT platform_workspaces_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspaces ADD CONSTRAINT platform_workspaces_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES cosa.users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_platform_workspaces_owner ON cosa.workspaces USING btree (owner_user_id);


CREATE TABLE IF NOT EXISTS cosa.user_workspace_module_preferences (
    workspace_id bigint NOT NULL,
    user_id bigint NOT NULL,
    module_key text NOT NULL,
    visible boolean DEFAULT true NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT user_workspace_module_preferences_module_key_check CHECK ((module_key = ANY (ARRAY['finance'::text, 'legal'::text, 'crm'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.user_workspace_module_preferences ADD CONSTRAINT user_workspace_module_preferences_pkey PRIMARY KEY (workspace_id, user_id, module_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.user_workspace_module_preferences ADD CONSTRAINT user_workspace_module_preferences_user_id_fkey FOREIGN KEY (user_id) REFERENCES cosa.users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.user_workspace_module_preferences ADD CONSTRAINT user_workspace_module_preferences_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES cosa.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS cosa.workspace_agent_policy (
    id bigint NOT NULL,
    platform_workspace_id bigint NOT NULL,
    tool_pattern text NOT NULL,
    decision text NOT NULL,
    reason text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT workspace_agent_policy_decision_check CHECK ((decision = ANY (ARRAY['ALLOW'::text, 'REQUIRE_APPROVAL'::text, 'DENY'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_agent_policy ADD CONSTRAINT workspace_agent_policy_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_agent_policy ADD CONSTRAINT workspace_agent_policy_platform_workspace_id_fkey FOREIGN KEY (platform_workspace_id) REFERENCES cosa.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_workspace_agent_policy_workspace_id ON cosa.workspace_agent_policy USING btree (platform_workspace_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_agent_policy_workspace_tool ON cosa.workspace_agent_policy USING btree (platform_workspace_id, tool_pattern);


CREATE TABLE IF NOT EXISTS cosa.workspace_business_policy_references (
    platform_workspace_id bigint NOT NULL,
    business_workspace_id text NOT NULL,
    version integer NOT NULL,
    policy_hash text NOT NULL,
    synced_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_business_policy_references ADD CONSTRAINT workspace_business_policy_references_pkey PRIMARY KEY (platform_workspace_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_business_policy_references ADD CONSTRAINT workspace_business_policy_references_platform_workspace_id_fkey FOREIGN KEY (platform_workspace_id) REFERENCES cosa.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS cosa.workspace_entitlements (
    platform_workspace_id bigint NOT NULL,
    plan_id text NOT NULL,
    effective_limits jsonb DEFAULT '{}'::jsonb NOT NULL,
    effective_features jsonb DEFAULT '{}'::jsonb NOT NULL,
    custom_overrides jsonb DEFAULT '{}'::jsonb NOT NULL,
    snapshot_signature text,
    last_issued_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_entitlements ADD CONSTRAINT workspace_entitlements_pkey PRIMARY KEY (platform_workspace_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_entitlements ADD CONSTRAINT workspace_entitlements_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES cosa.plans(id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_entitlements ADD CONSTRAINT workspace_entitlements_platform_workspace_id_fkey FOREIGN KEY (platform_workspace_id) REFERENCES cosa.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS cosa.workspace_invitations (
    id bigint NOT NULL,
    workspace_id bigint NOT NULL,
    email_normalized text NOT NULL,
    role_id text NOT NULL,
    token_hash text NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    invited_by_user_id bigint NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    accepted_at timestamp with time zone,
    revoked_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT workspace_invitations_role_id_check CHECK ((role_id = ANY (ARRAY['member'::text, 'admin'::text]))),
    CONSTRAINT workspace_invitations_status_check CHECK ((status = ANY (ARRAY['pending'::text, 'accepted'::text, 'revoked'::text, 'expired'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_invitations ADD CONSTRAINT workspace_invitations_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_invitations ADD CONSTRAINT workspace_invitations_invited_by_user_id_fkey FOREIGN KEY (invited_by_user_id) REFERENCES cosa.users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_invitations ADD CONSTRAINT workspace_invitations_role_id_fkey FOREIGN KEY (role_id) REFERENCES cosa.roles(id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_invitations ADD CONSTRAINT workspace_invitations_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES cosa.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_workspace_invitations_workspace ON cosa.workspace_invitations USING btree (workspace_id);

CREATE UNIQUE INDEX IF NOT EXISTS ux_workspace_invitations_pending_email ON cosa.workspace_invitations USING btree (workspace_id, email_normalized) WHERE (status = 'pending'::text);

CREATE UNIQUE INDEX IF NOT EXISTS ux_workspace_invitations_token_hash ON cosa.workspace_invitations USING btree (token_hash);


CREATE TABLE IF NOT EXISTS cosa.workspace_licenses (
    id bigint NOT NULL,
    platform_workspace_id bigint NOT NULL,
    plan_id text NOT NULL,
    license_key text NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    starts_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone,
    grace_period_days integer DEFAULT 7 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_licenses ADD CONSTRAINT workspace_licenses_license_key_key UNIQUE (license_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_licenses ADD CONSTRAINT workspace_licenses_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_licenses ADD CONSTRAINT workspace_licenses_platform_workspace_id_key UNIQUE (platform_workspace_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_licenses ADD CONSTRAINT workspace_licenses_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES cosa.plans(id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_licenses ADD CONSTRAINT workspace_licenses_platform_workspace_id_fkey FOREIGN KEY (platform_workspace_id) REFERENCES cosa.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS cosa.workspace_memberships (
    id bigint NOT NULL,
    platform_workspace_id bigint NOT NULL,
    user_id bigint NOT NULL,
    role text DEFAULT 'member'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT workspace_memberships_role_check CHECK ((role = ANY (ARRAY['founder'::text, 'co-founder'::text, 'admin'::text, 'member'::text, 'viewer'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_memberships ADD CONSTRAINT platform_workspace_membership_platform_workspace_id_user_id_key UNIQUE (platform_workspace_id, user_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_memberships ADD CONSTRAINT platform_workspace_memberships_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_memberships ADD CONSTRAINT platform_workspace_memberships_platform_workspace_id_fkey FOREIGN KEY (platform_workspace_id) REFERENCES cosa.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_memberships ADD CONSTRAINT platform_workspace_memberships_user_id_fkey FOREIGN KEY (user_id) REFERENCES cosa.users(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS cosa.workspace_module_configs (
    workspace_id bigint NOT NULL,
    module_key text NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    updated_by text NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT workspace_module_configs_module_key_check CHECK ((module_key = ANY (ARRAY['finance'::text, 'legal'::text, 'crm'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_module_configs ADD CONSTRAINT workspace_module_configs_pkey PRIMARY KEY (workspace_id, module_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_module_configs ADD CONSTRAINT workspace_module_configs_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES cosa.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


CREATE TABLE IF NOT EXISTS cosa.workspace_surface_overrides (
    workspace_id bigint NOT NULL,
    surface_key text NOT NULL,
    status_override text NOT NULL,
    reason text,
    updated_by text NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT workspace_surface_overrides_status_override_check CHECK ((status_override = ANY (ARRAY['PILOT'::text, 'PLANNED'::text, 'CONFIGURATION_REQUIRED'::text, 'UNAVAILABLE'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_surface_overrides ADD CONSTRAINT workspace_surface_overrides_pkey PRIMARY KEY (workspace_id, surface_key);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_surface_overrides ADD CONSTRAINT workspace_surface_overrides_workspace_id_fkey FOREIGN KEY (workspace_id) REFERENCES cosa.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE INDEX IF NOT EXISTS idx_workspace_surface_overrides_workspace ON cosa.workspace_surface_overrides USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS cosa.workspace_sync_log (
    id bigint NOT NULL,
    platform_workspace_id bigint NOT NULL,
    client_creation_id text NOT NULL,
    sync_status text DEFAULT 'pending'::text NOT NULL,
    error_msg text,
    synced_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT platform_workspace_sync_log_sync_status_check CHECK ((sync_status = ANY (ARRAY['pending'::text, 'success'::text, 'failed'::text])))
);

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_sync_log ADD CONSTRAINT platform_workspace_sync_log_client_creation_id_key UNIQUE (client_creation_id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_sync_log ADD CONSTRAINT platform_workspace_sync_log_pkey PRIMARY KEY (id);
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE ONLY cosa.workspace_sync_log ADD CONSTRAINT platform_workspace_sync_log_platform_workspace_id_fkey FOREIGN KEY (platform_workspace_id) REFERENCES cosa.workspaces(id) ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;


INSERT INTO cosa.roles (id, name, category, sort_order, description) VALUES
  ('founder',    'Sáng lập',      'leadership', 1,  'Nhà sáng lập doanh nghiệp / workspace'),
  ('co-founder', 'Đồng sáng lập', 'leadership', 2,  'Đồng sáng lập doanh nghiệp / workspace'),
  ('mentor',     'Cố vấn',        'community',  3,  'Cố vấn chuyên môn và phát triển doanh nghiệp'),
  ('investor',   'Nhà đầu tư',    'community',  4,  'Nhà đầu tư / Quỹ đầu tư mạo hiểm'),
  ('tech',       'Công nghệ',     'department', 5,  'Khối Kỹ thuật & Công nghệ'),
  ('marketing',  'Marketing',     'department', 6,  'Khối Tiếp thị & Truyền thông'),
  ('sales',      'Kinh doanh',    'department', 7,  'Khối Bán hàng & Phát triển thị trường'),
  ('finance',    'Tài chính',     'department', 8,  'Khối Kế toán & Tài chính'),
  ('hr',         'Nhân sự',       'department', 9,  'Khối Quản trị nhân sự'),
  ('operations', 'Vận hành',      'department', 10, 'Khối Vận hành doanh nghiệp'),
  ('member',     'Thành viên',    'community',  11, 'Thành viên chung'),
  ('superadmin', 'Quản trị viên', 'system',     12, 'Quản trị tối cao toàn bộ nền tảng'),
  ('support',    'Hỗ trợ viên',   'system',     13, 'Hỗ trợ khách hàng và vận hành hệ thống')
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name,
    category = EXCLUDED.category,
    sort_order = EXCLUDED.sort_order,
    description = EXCLUDED.description;

INSERT INTO cosa.plans (id, name, description) VALUES
  ('free', 'Free Plan', 'Free tier for exploration'),
  ('starter', 'Starter Plan', 'Default plan for new workspaces'),
  ('pro', 'Pro Plan', 'For growing companies'),
  ('enterprise', 'Enterprise Plan', 'For large organizations')
ON CONFLICT (id) DO NOTHING;

-- Task 0 — Khôi phục Control Plane execution substrate bị đợt squash baseline
-- Founder Trial R1 (commit 81461673) xoá khỏi migration history NHƯNG code đang
-- chạy vẫn phụ thuộc:
--   * services/cosa/storage/control-plane-schema.ts  (workers, runtime_leases, scheduled_tasks)
--   * services/cosa/services/control-plane-scheduler.service.ts / control-plane-lease.service.ts
--     / child-scheduler.service.ts + services/cosa/control-plane.cron.ts (reclaimStuckTasks)
--   * apps/cosa/worker/main.py (plane.scheduler.* + plane.lease_client.*)
--
-- Đây là state PHẲNG cuối cùng của các migration đã xoá:
--   7_control_plane_leases_workers  + 10_scheduled_tasks_durable_claims
--   + 16_scheduled_task_child_edges + 17_scheduled_task_status_blocked
-- Schema `control_plane` đã tồn tại từ 001_founder_trial_mvp_baseline. Thuần
-- expand-only: CREATE ... IF NOT EXISTS, không DROP/ALTER cột sẵn có.
-- KHÔNG khôi phục missions/tasks/assignments/watches/trigger_policies/
-- signal_observations/delivery_*/cost_ledger (dormant, không có consumer
-- production) và workspace_execution_leases/workspace_runtime_nodes (M5/M6
-- local-vs-cloud failover, ngoài happy path dispatch).

CREATE TABLE IF NOT EXISTS control_plane.workers (
    id TEXT PRIMARY KEY,
    runtime_kind TEXT NOT NULL,
    endpoint TEXT,
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    concurrency_limit INTEGER NOT NULL DEFAULT 1,
    trust_tier TEXT NOT NULL DEFAULT 'T0',
    last_heartbeat_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'online' CHECK (status IN ('online', 'offline', 'degraded')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Thay packages/agent/runs/leases.py::RunLeaseManager (in-memory) — khoá thực
-- thi phân tán chống split-brain thật giữa nhiều process. 1 run_id ≤ 1 lease.
CREATE TABLE IF NOT EXISTS control_plane.runtime_leases (
    run_id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL REFERENCES control_plane.workers(id) ON DELETE CASCADE,
    lease_token TEXT NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    heartbeat_interval_sec INTEGER NOT NULL DEFAULT 30
);

-- Thay packages/agent/coordination/scheduler.py::RunScheduler (in-memory).
-- Cột attempt_count..dead_letter_reason: Phase 3 Durable Queue Recovery
-- (claim atomic bằng fencing token claim_token + retry backoff + dead-letter).
-- Cột parent_task_id..completion_key: P1 durable hierarchical supervisor.
-- CHECK status có 'blocked' (child task chờ depends_on) — đặt tên constraint
-- tường minh để migration sau ALTER được.
CREATE TABLE IF NOT EXISTS control_plane.scheduled_tasks (
    id TEXT PRIMARY KEY,
    coalescing_key TEXT,
    target_spec_id TEXT NOT NULL,
    target_spec_kind TEXT NOT NULL DEFAULT 'agent',
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    claimed_by TEXT,
    claim_token TEXT,
    claimed_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ,
    visibility_timeout_at TIMESTAMPTZ,
    last_error TEXT,
    next_retry_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    dead_letter_reason TEXT,
    parent_task_id TEXT,
    child_id TEXT,
    depends_on JSONB NOT NULL DEFAULT '[]'::jsonb,
    join_policy TEXT,
    join_quorum INTEGER,
    child_result JSONB,
    completion_key TEXT,
    CONSTRAINT scheduled_tasks_status_check
        CHECK (status IN ('scheduled', 'processing', 'completed', 'coalesced', 'failed', 'blocked'))
);

-- Chỉ 1 task 'scheduled' đang chờ cho mỗi coalescing_key — khớp hành vi coalesce
-- của RunScheduler gốc.
CREATE UNIQUE INDEX IF NOT EXISTS idx_control_plane_scheduled_tasks_coalescing_key_pending
    ON control_plane.scheduled_tasks (coalescing_key)
    WHERE status = 'scheduled' AND coalescing_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_control_plane_scheduled_tasks_status_run_at
    ON control_plane.scheduled_tasks (status, run_at);
-- Sweeper (cron) quét đúng tập nhỏ: processing đã hết visibility timeout.
CREATE INDEX IF NOT EXISTS idx_control_plane_scheduled_tasks_visibility_timeout
    ON control_plane.scheduled_tasks (visibility_timeout_at)
    WHERE status = 'processing';
CREATE INDEX IF NOT EXISTS idx_control_plane_scheduled_tasks_next_retry
    ON control_plane.scheduled_tasks (next_retry_at)
    WHERE status = 'scheduled' AND next_retry_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_parent
    ON control_plane.scheduled_tasks (parent_task_id)
    WHERE parent_task_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_scheduled_tasks_parent_child
    ON control_plane.scheduled_tasks (parent_task_id, child_id)
    WHERE parent_task_id IS NOT NULL;

-- SP-A: restore control_plane.document_ingestion* dropped by the 001 cosa squash.
-- Flattened from deleted 15_document_ingestions.up.sql (git ref 81461673^),
-- matching control-plane-schema.ts. Expand-only, idempotent. Audit id is
-- GENERATED IDENTITY (Drizzle) not BIGSERIAL (old migration).
CREATE SCHEMA IF NOT EXISTS control_plane;

CREATE TABLE IF NOT EXISTS control_plane.document_ingestions (
  id                    TEXT PRIMARY KEY,
  workspace_id          TEXT NOT NULL,
  created_by            TEXT NOT NULL,
  original_filename     TEXT NOT NULL,
  declared_media_type   TEXT NOT NULL,
  detected_media_type   TEXT,
  size_bytes            BIGINT,
  source_sha256         TEXT,
  original_object_key   TEXT,
  state                 TEXT NOT NULL CHECK (state IN ('UPLOADING', 'QUARANTINED', 'QUEUED', 'VALIDATING', 'CONVERTING', 'REVIEW_PENDING', 'PUBLISHED', 'REJECTED', 'FAILED', 'EXPIRED')),
  idempotency_key       TEXT NOT NULL,
  knowledge_source_id   TEXT,
  converter_spec_id     TEXT,
  manifest_json         JSONB,
  failure_code          TEXT,
  claim_token           TEXT,
  created_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  UNIQUE (workspace_id, created_by, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_document_ingestions_workspace_state_created
  ON control_plane.document_ingestions (workspace_id, state, created_at DESC);

CREATE TABLE IF NOT EXISTS control_plane.document_ingestion_audit_events (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ingestion_id  TEXT NOT NULL REFERENCES control_plane.document_ingestions(id) ON DELETE CASCADE,
  actor_kind    TEXT NOT NULL CHECK (actor_kind IN ('user', 'worker', 'system')),
  actor_id      TEXT NOT NULL,
  old_state     TEXT,
  new_state     TEXT NOT NULL,
  reason        TEXT,
  failure_code  TEXT,
  created_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_ingestion_audit_events_ingestion_created
  ON control_plane.document_ingestion_audit_events (ingestion_id, created_at DESC);
