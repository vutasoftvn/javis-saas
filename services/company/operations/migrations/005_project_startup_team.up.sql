-- Migration 005: Project Startup Team & Durable Assignments
-- Tạo type, bảng quản lý startup team per project, và backfill TEMPLATE cho toàn bộ project hiện có.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'project_agent_assignment_state' AND typnamespace = 'operating'::regnamespace) THEN
    CREATE TYPE operating.project_agent_assignment_state
      AS ENUM ('TEMPLATE', 'ACTIVE', 'PAUSED', 'RETIRED');
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS operating.project_agent_assignments (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  project_id bigint NOT NULL,
  profile_key text NOT NULL,
  state operating.project_agent_assignment_state NOT NULL DEFAULT 'TEMPLATE',
  agent_workforce_member_id bigint,
  spec_id text,
  spec_version text,
  spec_hash text,
  activation_policy_snapshot jsonb,
  version integer NOT NULL DEFAULT 1,
  disabled_reason text,
  created_by bigint,
  activated_by bigint,
  paused_by bigint,
  activated_at timestamptz,
  paused_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uix_project_agent_assignments_ws_proj_key UNIQUE (workspace_id, project_id, profile_key),
  CONSTRAINT fk_project_agent_assignments_proj_ws FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS operating.project_agent_assignment_events (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  project_id bigint NOT NULL,
  assignment_id bigint NOT NULL REFERENCES operating.project_agent_assignments(id) ON DELETE CASCADE,
  event_type text NOT NULL,
  from_state operating.project_agent_assignment_state,
  to_state operating.project_agent_assignment_state NOT NULL,
  assignment_version integer NOT NULL,
  actor_id bigint NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  event_payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_project_agent_assignments_ws_proj
  ON operating.project_agent_assignments (workspace_id, project_id);

CREATE INDEX IF NOT EXISTS idx_project_agent_assignment_events_assignment
  ON operating.project_agent_assignment_events (assignment_id, occurred_at DESC);

-- Backfill idempotently: Mỗi project hiện có nhận 9 catalog template assignments
CREATE SEQUENCE IF NOT EXISTS operating.temp_assignment_id_seq START WITH 1000;

INSERT INTO operating.project_agent_assignments (
  id,
  workspace_id,
  project_id,
  profile_key,
  state,
  disabled_reason,
  version,
  created_at,
  updated_at
)
SELECT
  (((extract(epoch from now()) * 1000)::bigint - 1704067200000) << 23) + nextval('operating.temp_assignment_id_seq'),
  p.workspace_id,
  p.id,
  cat.profile_key,
  'TEMPLATE'::operating.project_agent_assignment_state,
  cat.disabled_reason,
  1,
  now(),
  now()
FROM strategy.projects p
CROSS JOIN (
  VALUES
    ('founder_assistant', NULL::text),
    ('research_intelligence', NULL::text),
    ('strategy', NULL::text),
    ('marketing', NULL::text),
    ('finance', NULL::text),
    ('crm', 'PENDING_CRM_FOUNDATION'::text),
    ('sales', 'PENDING_CRM_FOUNDATION'::text),
    ('coding', 'DEFERRED_CODING'::text),
    ('customer_support', 'PENDING_PROJECT_KNOWLEDGE'::text)
) AS cat(profile_key, disabled_reason)
ON CONFLICT (workspace_id, project_id, profile_key) DO NOTHING;

DROP SEQUENCE IF EXISTS operating.temp_assignment_id_seq;
