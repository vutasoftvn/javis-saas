-- COSA Startup Core baseline migration for packages/agent
-- Replaces Founder Trial baseline with clean-slate Agent execution, conversation,
-- governance, models, and event-intake substrate.

CREATE SCHEMA IF NOT EXISTS agent;
CREATE SCHEMA IF NOT EXISTS agent_conversation;
CREATE SCHEMA IF NOT EXISTS agent_governance;
CREATE SCHEMA IF NOT EXISTS agent_registry;
CREATE SCHEMA IF NOT EXISTS models;

CREATE TABLE IF NOT EXISTS agent.agent_web_search_budget (
    workspace_id character varying(64) NOT NULL,
    window_start date NOT NULL,
    query_count integer DEFAULT 0 NOT NULL,
    cost_accumulated numeric(12,4) DEFAULT 0.0 NOT NULL,
    daily_query_cap integer DEFAULT 100 NOT NULL,
    daily_cost_cap numeric(12,4) DEFAULT 10.0 NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT agent_web_search_budget_pkey PRIMARY KEY (workspace_id, window_start)
);

CREATE INDEX IF NOT EXISTS idx_agent_web_search_budget_workspace ON agent.agent_web_search_budget USING btree (workspace_id, window_start DESC);


CREATE TABLE IF NOT EXISTS agent.runs (
    run_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    conversation_id character varying(64),
    session_ref character varying(128),
    principal character varying(128) NOT NULL,
    root_executable_id character varying(128) NOT NULL,
    root_executable_kind character varying(32) DEFAULT 'agent'::character varying NOT NULL,
    root_executable_version character varying(32) DEFAULT '1.0.0'::character varying NOT NULL,
    root_definition_hash character varying(64),
    status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    execution_mode character varying(32) DEFAULT 'autonomous'::character varying NOT NULL,
    correlation_id character varying(128),
    idempotency_key character varying(128),
    input_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    model_policy jsonb DEFAULT '{}'::jsonb NOT NULL,
    final_output jsonb,
    usage jsonb DEFAULT '{}'::jsonb NOT NULL,
    error_details jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    wf_agent_instance_id uuid,
    wf_assignment_id uuid,
    wf_work_package_id text,
    wf_work_attempt_id text,
    CONSTRAINT runs_pkey PRIMARY KEY (run_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_correlation ON agent.runs USING btree (correlation_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_idempotency ON agent.runs USING btree (idempotency_key);
CREATE INDEX IF NOT EXISTS idx_agent_runs_wf_attempt ON agent.runs USING btree (wf_work_attempt_id) WHERE (wf_work_attempt_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_agent_runs_wf_employee ON agent.runs USING btree (workspace_id, wf_agent_instance_id) WHERE (wf_agent_instance_id IS NOT NULL);
CREATE INDEX IF NOT EXISTS idx_agent_runs_workspace_status ON agent.runs USING btree (workspace_id, status);


CREATE TABLE IF NOT EXISTS agent.run_tool_calls (
    tool_call_id character varying(128) NOT NULL,
    run_id character varying(64) NOT NULL,
    checkpoint_ref character varying(128),
    capability_id character varying(128) NOT NULL,
    payload_hash character varying(64) NOT NULL,
    input_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    idempotency_key character varying(128),
    result_hash character varying(64),
    output_payload jsonb,
    error_message text,
    execution_target_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    governance_state jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    CONSTRAINT run_tool_calls_pkey PRIMARY KEY (run_id, tool_call_id),
    CONSTRAINT uq_agent_run_tool_calls_tool_call_id UNIQUE (tool_call_id),
    CONSTRAINT run_tool_calls_run_id_fkey FOREIGN KEY (run_id) REFERENCES agent.runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_cap ON agent.run_tool_calls USING btree (capability_id);
CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_idempotency ON agent.run_tool_calls USING btree (run_id, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_agent_tool_calls_run ON agent.run_tool_calls USING btree (run_id);


CREATE TABLE IF NOT EXISTS agent.approvals (
    approval_id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    tool_call_id character varying(128) NOT NULL,
    checkpoint_ref character varying(128) NOT NULL,
    status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    requirement jsonb DEFAULT '{}'::jsonb NOT NULL,
    requester character varying(128),
    action character varying(128),
    subject text,
    reviewer character varying(128),
    reason text,
    evidence jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    decided_at timestamp with time zone,
    expires_at timestamp with time zone,
    decision_version integer DEFAULT 0 NOT NULL,
    CONSTRAINT approvals_pkey PRIMARY KEY (approval_id),
    CONSTRAINT approvals_run_id_fkey FOREIGN KEY (run_id) REFERENCES agent.runs(run_id) ON DELETE CASCADE,
    CONSTRAINT approvals_run_tool_call_fkey FOREIGN KEY (run_id, tool_call_id) REFERENCES agent.run_tool_calls(run_id, tool_call_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_approvals_checkpoint ON agent.approvals USING btree (checkpoint_ref);
CREATE INDEX IF NOT EXISTS idx_agent_approvals_run ON agent.approvals USING btree (run_id);
CREATE INDEX IF NOT EXISTS idx_agent_approvals_status ON agent.approvals USING btree (status);
CREATE INDEX IF NOT EXISTS idx_agent_approvals_tool_call ON agent.approvals USING btree (tool_call_id);


CREATE TABLE IF NOT EXISTS agent.idempotency_claims (
    claim_id character varying(64) NOT NULL,
    tenant_id character varying(64),
    capability_id character varying(128) NOT NULL,
    scope_kind character varying(32) DEFAULT 'RUN'::character varying NOT NULL,
    scope_key character varying(128) NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    payload_hash character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    tool_call_id character varying(128) NOT NULL,
    status character varying(32) DEFAULT 'running'::character varying NOT NULL,
    result_hash character varying(64),
    result_payload jsonb,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT idempotency_claims_pkey PRIMARY KEY (claim_id),
    CONSTRAINT uq_agent_idempotency_claims_scope UNIQUE (scope_kind, scope_key, capability_id, idempotency_key),
    CONSTRAINT idempotency_claims_run_id_fkey FOREIGN KEY (run_id) REFERENCES agent.runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_idempotency_claims_run ON agent.idempotency_claims USING btree (run_id);
CREATE INDEX IF NOT EXISTS idx_agent_idempotency_claims_status ON agent.idempotency_claims USING btree (status);


CREATE TABLE IF NOT EXISTS agent.run_checkpoints (
    checkpoint_ref character varying(128) NOT NULL,
    run_id character varying(64) NOT NULL,
    sequence_no integer NOT NULL,
    step_name character varying(128),
    state_kind character varying(32) DEFAULT 'workflow'::character varying NOT NULL,
    serialized_state jsonb DEFAULT '{}'::jsonb NOT NULL,
    manifest_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    resume_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT run_checkpoints_pkey PRIMARY KEY (checkpoint_ref),
    CONSTRAINT uq_agent_checkpoint_run_seq UNIQUE (run_id, sequence_no),
    CONSTRAINT run_checkpoints_run_id_fkey FOREIGN KEY (run_id) REFERENCES agent.runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_checkpoints_run ON agent.run_checkpoints USING btree (run_id);


CREATE TABLE IF NOT EXISTS agent.run_cost_observations (
    observation_id uuid NOT NULL,
    workspace_id text NOT NULL,
    run_id text NOT NULL,
    provider_key text NOT NULL,
    model_key text NOT NULL,
    input_tokens bigint,
    output_tokens bigint,
    cost_amount numeric,
    currency text,
    observed_at timestamp with time zone NOT NULL,
    CONSTRAINT run_cost_observations_pkey PRIMARY KEY (observation_id),
    CONSTRAINT run_cost_observations_cost_amount_check CHECK ((cost_amount >= (0)::numeric)),
    CONSTRAINT run_cost_observations_input_tokens_check CHECK ((input_tokens >= 0)),
    CONSTRAINT run_cost_observations_output_tokens_check CHECK ((output_tokens >= 0)),
    CONSTRAINT run_cost_observations_workspace_id_run_id_provider_key_mode_key UNIQUE (workspace_id, run_id, provider_key, model_key, observed_at)
);

CREATE INDEX IF NOT EXISTS idx_run_cost_observations_ws_time ON agent.run_cost_observations USING btree (workspace_id, observed_at DESC);


CREATE TABLE IF NOT EXISTS agent.run_events (
    event_id character varying(64) NOT NULL,
    run_id character varying(64) NOT NULL,
    sequence_no bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
    event_type character varying(64) NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    correlation_id character varying(128),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT run_events_pkey PRIMARY KEY (event_id),
    CONSTRAINT run_events_run_id_fkey FOREIGN KEY (run_id) REFERENCES agent.runs(run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_events_run_seq ON agent.run_events USING btree (run_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_agent_events_type ON agent.run_events USING btree (event_type);


CREATE TABLE IF NOT EXISTS agent.runtime_signal_outbox (
    outbox_id uuid NOT NULL,
    workspace_id text NOT NULL,
    source_kind text NOT NULL,
    source_id text NOT NULL,
    sequence bigint NOT NULL,
    state text NOT NULL,
    observed_at timestamp with time zone NOT NULL,
    correlation_id text NOT NULL,
    payload_hash text NOT NULL,
    state_delivery text NOT NULL,
    attempt_count integer DEFAULT 0 NOT NULL,
    next_attempt_at timestamp with time zone DEFAULT now() NOT NULL,
    delivered_at timestamp with time zone,
    CONSTRAINT runtime_signal_outbox_pkey PRIMARY KEY (outbox_id),
    CONSTRAINT runtime_signal_outbox_state_delivery_check CHECK ((state_delivery = ANY (ARRAY['PENDING'::text, 'DELIVERED'::text, 'FAILED'::text]))),
    CONSTRAINT runtime_signal_outbox_workspace_id_source_kind_source_id_se_key UNIQUE (workspace_id, source_kind, source_id, sequence)
);

CREATE INDEX IF NOT EXISTS idx_runtime_signal_outbox_pending ON agent.runtime_signal_outbox USING btree (state_delivery, next_attempt_at);


CREATE TABLE IF NOT EXISTS agent_conversation.conversations (
    conversation_id character varying(64) NOT NULL,
    workspace_id character varying(64) NOT NULL,
    created_by_principal character varying(128) NOT NULL,
    title character varying(256) DEFAULT 'New Conversation'::character varying NOT NULL,
    active_agent_profile character varying(128),
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    archived_at timestamp with time zone,
    CONSTRAINT conversations_pkey PRIMARY KEY (conversation_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_conversation_conversations_workspace ON agent_conversation.conversations USING btree (workspace_id, archived_at);


CREATE TABLE IF NOT EXISTS agent_conversation.messages (
    message_id character varying(64) NOT NULL,
    conversation_id character varying(64) NOT NULL,
    sequence_no bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
    role character varying(32) NOT NULL,
    content text NOT NULL,
    run_id character varying(64),
    parent_message_id character varying(64),
    status character varying(32) DEFAULT 'completed'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT messages_pkey PRIMARY KEY (message_id),
    CONSTRAINT uq_agent_conversation_messages_conv_seq UNIQUE (conversation_id, sequence_no),
    CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES agent_conversation.conversations(conversation_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_conversation_messages_conv ON agent_conversation.messages USING btree (conversation_id, sequence_no);
CREATE INDEX IF NOT EXISTS idx_agent_conversation_messages_run ON agent_conversation.messages USING btree (run_id);


CREATE TABLE IF NOT EXISTS agent_conversation.message_attachments (
    attachment_id character varying(64) NOT NULL,
    message_id character varying(64) NOT NULL,
    object_ref text NOT NULL,
    media_type character varying(128) NOT NULL,
    file_name character varying(256) NOT NULL,
    size bigint DEFAULT 0 NOT NULL,
    checksum character varying(128),
    knowledge_ingest_status character varying(32) DEFAULT 'COMPLETED'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT message_attachments_pkey PRIMARY KEY (attachment_id),
    CONSTRAINT message_attachments_message_id_fkey FOREIGN KEY (message_id) REFERENCES agent_conversation.messages(message_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_agent_conversation_attachments_message ON agent_conversation.message_attachments USING btree (message_id);


CREATE TABLE IF NOT EXISTS agent_conversation.run_stream_events (
    sequence bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
    run_id character varying(64) NOT NULL,
    event_type character varying(64) NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    conversation_id character varying(64) NOT NULL,
    correlation_id character varying(64),
    schema_version smallint DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT run_stream_events_pkey PRIMARY KEY (sequence)
);

CREATE INDEX IF NOT EXISTS idx_run_stream_events_conversation ON agent_conversation.run_stream_events USING btree (conversation_id);
CREATE INDEX IF NOT EXISTS idx_run_stream_events_run_seq ON agent_conversation.run_stream_events USING btree (run_id, sequence);


CREATE TABLE IF NOT EXISTS agent_governance.approval_evidence (
    id text NOT NULL,
    approver text NOT NULL,
    scope text NOT NULL,
    decided_at text NOT NULL,
    valid_until text,
    CONSTRAINT approval_evidence_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_approval_evidence_scope ON agent_governance.approval_evidence USING btree (scope);


CREATE TABLE IF NOT EXISTS agent_governance.invocation_governance_history (
    id text NOT NULL,
    run_id text NOT NULL,
    tool_call_id text NOT NULL,
    observation jsonb NOT NULL,
    source text NOT NULL,
    observed_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT invocation_governance_history_source_check CHECK ((source = ANY (ARRAY['ambient'::text, 'historical'::text]))),
    CONSTRAINT invocation_governance_history_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_invocation_governance_history_invocation ON agent_governance.invocation_governance_history USING btree (run_id, tool_call_id, observed_at);


CREATE TABLE IF NOT EXISTS agent_governance.invocation_governance_state (
    run_id text NOT NULL,
    tool_call_id text NOT NULL,
    accumulated jsonb NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT invocation_governance_state_pkey PRIMARY KEY (run_id, tool_call_id)
);


CREATE TABLE IF NOT EXISTS agent_governance.spec_resolution_manifest_entries (
    run_id text NOT NULL,
    spec_kind text NOT NULL,
    spec_id text NOT NULL,
    spec_version text NOT NULL,
    definition_hash text NOT NULL,
    resolved_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT spec_resolution_manifest_entries_spec_kind_check CHECK ((spec_kind = ANY (ARRAY['agent'::text, 'workflow'::text, 'skill'::text, 'prompt'::text, 'model_policy'::text, 'tool_contract'::text]))),
    CONSTRAINT spec_resolution_manifest_entries_pkey PRIMARY KEY (run_id, spec_kind, spec_id, definition_hash)
);

CREATE INDEX IF NOT EXISTS idx_spec_resolution_manifest_run_id ON agent_governance.spec_resolution_manifest_entries USING btree (run_id);


CREATE TABLE IF NOT EXISTS agent_registry.published_specs (
    spec_kind character varying(32) NOT NULL,
    spec_id character varying(128) NOT NULL,
    version character varying(32) NOT NULL,
    definition_hash character varying(64) NOT NULL,
    content jsonb NOT NULL,
    status character varying(32) DEFAULT 'published'::character varying NOT NULL,
    publisher character varying(128),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    published_at timestamp with time zone DEFAULT now() NOT NULL,
    retired_at timestamp with time zone,
    CONSTRAINT published_specs_pkey PRIMARY KEY (spec_kind, spec_id, version),
    CONSTRAINT uq_agent_registry_published_specs_hash UNIQUE (spec_kind, spec_id, definition_hash)
);

CREATE INDEX IF NOT EXISTS idx_agent_registry_published_specs_status ON agent_registry.published_specs USING btree (status);


CREATE TABLE IF NOT EXISTS models.model_provider_profiles (
    workspace_id text NOT NULL,
    profile_id text NOT NULL,
    provider_type text NOT NULL,
    model_id text NOT NULL,
    credential_ref text,
    allowed_models jsonb DEFAULT '[]'::jsonb NOT NULL,
    budget_usd_limit numeric,
    max_concurrency integer,
    status text DEFAULT 'ACTIVE'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    base_url text,
    CONSTRAINT model_provider_profiles_pkey PRIMARY KEY (workspace_id, profile_id),
    CONSTRAINT model_provider_profiles_max_concurrency_check CHECK (((max_concurrency IS NULL) OR (max_concurrency > 0))),
    CONSTRAINT model_provider_profiles_provider_type_check CHECK ((provider_type = ANY (ARRAY['local_openai_compatible'::text, 'anthropic_api'::text, 'openai_api'::text, 'openrouter_api'::text, 'deepseek_api'::text, 'claude_cli'::text, 'codex_cli'::text, 'gemini_cli'::text]))),
    CONSTRAINT model_provider_profiles_status_check CHECK ((status = ANY (ARRAY['ACTIVE'::text, 'DISABLED'::text])))
);

CREATE INDEX IF NOT EXISTS idx_model_provider_profiles_workspace_status ON models.model_provider_profiles USING btree (workspace_id, status);


CREATE TABLE IF NOT EXISTS models.workspace_credentials (
    workspace_id text NOT NULL,
    credential_id text NOT NULL,
    ciphertext text NOT NULL,
    key_version integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT workspace_credentials_pkey PRIMARY KEY (workspace_id, credential_id)
);

CREATE INDEX IF NOT EXISTS idx_workspace_credentials_workspace ON models.workspace_credentials USING btree (workspace_id);


CREATE TABLE IF NOT EXISTS models.workspace_model_policies (
    workspace_id text NOT NULL,
    scope text NOT NULL,
    scope_key text NOT NULL,
    primary_profile_id text NOT NULL,
    fallback_profile_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT workspace_model_policies_pkey PRIMARY KEY (workspace_id, scope, scope_key),
    CONSTRAINT workspace_model_policies_scope_check CHECK ((scope = ANY (ARRAY['WORKSPACE'::text, 'AGENT_PROFILE'::text]))),
    CONSTRAINT workspace_model_policies_workspace_id_primary_profile_id_fkey FOREIGN KEY (workspace_id, primary_profile_id) REFERENCES models.model_provider_profiles(workspace_id, profile_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_workspace_model_policies_workspace_scope ON models.workspace_model_policies USING btree (workspace_id, scope);


-- Event-intake substrate in public schema
CREATE TABLE IF NOT EXISTS public.event_inbox (
  id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  workspace_id      TEXT        NOT NULL,
  event_id          UUID        NOT NULL,
  consumer_name     TEXT        NOT NULL,
  event_type        TEXT        NOT NULL,
  correlation_id    TEXT        NOT NULL,
  received_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  outcome           TEXT        NOT NULL,
  scheduled_task_id TEXT,
  aggregate_type    TEXT,
  aggregate_id      TEXT,
  UNIQUE (workspace_id, event_id, consumer_name)
);

CREATE INDEX IF NOT EXISTS idx_event_inbox_correlation
  ON public.event_inbox (workspace_id, correlation_id);
CREATE INDEX IF NOT EXISTS idx_event_inbox_agg_day
  ON public.event_inbox (workspace_id, aggregate_id, received_at);

CREATE TABLE IF NOT EXISTS public.event_trigger_rules (
  rule_id                        TEXT PRIMARY KEY,
  workspace_id                   TEXT        NOT NULL,
  event_type                     TEXT        NOT NULL,
  agent_spec_id                  TEXT        NOT NULL,
  agent_spec_version             TEXT        NOT NULL,
  agent_spec_hash                TEXT        NOT NULL,
  mode                           TEXT        NOT NULL
                                   CHECK (mode IN ('artifact_only', 'proposal', 'write')),
  max_runs_per_aggregate_per_day INTEGER     NOT NULL DEFAULT 1,
  required_capabilities          JSONB       NOT NULL DEFAULT '[]'::jsonb,
  aggregate_filter               JSONB,
  owner                          TEXT        NOT NULL DEFAULT 'operator',
  enabled                        BOOLEAN     NOT NULL DEFAULT false,
  eval_evidence_ref              TEXT,
  event_schema_version           INTEGER     NOT NULL DEFAULT 1,
  created_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, event_type)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.event_inbox         TO agent_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.event_trigger_rules TO agent_app;
