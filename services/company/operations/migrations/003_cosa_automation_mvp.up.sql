-- COSA Automation MVP (Task 1) — Company-owned automation definitions, immutable
-- revisions, invocations and the invocation audit event stream.
-- docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md
--
-- Expand-only. All tables in schema `operating`. Snowflake bigint PKs supplied by
-- the app (shared/services/snowflake.service.ts). Tenant-leading indexes. No FK
-- crosses a database boundary — every FK here stays inside the Company DB.

CREATE TABLE IF NOT EXISTS operating.automation_definitions (
  id                  bigint PRIMARY KEY,
  workspace_id        bigint NOT NULL,
  automation_key      text NOT NULL,
  current_revision_id bigint,
  lifecycle_state     text NOT NULL DEFAULT 'DRAFT'
                        CHECK (lifecycle_state IN ('DRAFT', 'PUBLISHED', 'SUSPENDED', 'RETIRED')),
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  deleted_at          timestamptz
);
CREATE UNIQUE INDEX IF NOT EXISTS uix_automation_definitions_ws_key
  ON operating.automation_definitions (workspace_id, automation_key)
  WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_automation_definitions_workspace
  ON operating.automation_definitions (workspace_id);

CREATE TABLE IF NOT EXISTS operating.automation_revisions (
  id                       bigint PRIMARY KEY,
  workspace_id             bigint NOT NULL,
  definition_id            bigint NOT NULL
                             REFERENCES operating.automation_definitions(id) ON DELETE CASCADE,
  revision_no              integer NOT NULL,
  revision_hash            text NOT NULL,
  configuration_json       jsonb NOT NULL DEFAULT '{}'::jsonb,
  trigger_contract_json    jsonb NOT NULL DEFAULT '{}'::jsonb,
  capability_ids           jsonb NOT NULL DEFAULT '[]'::jsonb,
  evidence_contract_json   jsonb NOT NULL DEFAULT '{}'::jsonb,
  autonomy_class           text NOT NULL DEFAULT 'read_only'
                             CHECK (autonomy_class IN ('read_only', 'draft_only', 'gated_effect')),
  approval_contract_json   jsonb NOT NULL DEFAULT '{}'::jsonb,
  pinned_dependencies_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  effective_policy_revision text,
  created_by               text NOT NULL,
  published_at             timestamptz,
  created_at               timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uix_automation_revisions_definition_no
  ON operating.automation_revisions (definition_id, revision_no);
CREATE INDEX IF NOT EXISTS idx_automation_revisions_ws_definition
  ON operating.automation_revisions (workspace_id, definition_id, revision_no DESC);

CREATE TABLE IF NOT EXISTS operating.automation_invocations (
  id                    bigint PRIMARY KEY,
  workspace_id          bigint NOT NULL,
  definition_id         bigint NOT NULL
                          REFERENCES operating.automation_definitions(id) ON DELETE CASCADE,
  revision_id           bigint NOT NULL
                          REFERENCES operating.automation_revisions(id) ON DELETE CASCADE,
  automation_key        text NOT NULL,
  revision_no           integer NOT NULL,
  revision_hash         text NOT NULL,
  idempotency_key       text NOT NULL,
  trigger_kind          text NOT NULL CHECK (trigger_kind IN ('manual', 'schedule', 'business_event')),
  trigger_identity      text NOT NULL,
  caller_principal      text NOT NULL,
  source                text NOT NULL,
  business_scope_json   jsonb NOT NULL DEFAULT '{}'::jsonb,
  validated_input_ref   text,
  fingerprint_hash      text NOT NULL,
  state                 text NOT NULL DEFAULT 'REQUESTED'
                          CHECK (state IN ('REQUESTED', 'QUEUED', 'LEASED', 'RUNNING',
                                           'WAITING_APPROVAL', 'COMPLETED', 'FAILED',
                                           'CANCELLED', 'BLOCKED', 'CANCEL_REQUESTED')),
  blocked_reason        text,
  agent_run_id          text,
  correlation_id        text NOT NULL,
  version               integer NOT NULL DEFAULT 1,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uix_automation_invocations_identity
  ON operating.automation_invocations (workspace_id, revision_id, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_automation_invocations_ws_state
  ON operating.automation_invocations (workspace_id, state, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_automation_invocations_ws_run
  ON operating.automation_invocations (workspace_id, agent_run_id);

CREATE TABLE IF NOT EXISTS operating.automation_invocation_events (
  id             bigint PRIMARY KEY,
  workspace_id   bigint NOT NULL,
  invocation_id  bigint NOT NULL
                   REFERENCES operating.automation_invocations(id) ON DELETE CASCADE,
  seq            integer NOT NULL,
  event_type     text NOT NULL,
  payload_json   jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uix_automation_invocation_events_seq
  ON operating.automation_invocation_events (workspace_id, invocation_id, seq);
