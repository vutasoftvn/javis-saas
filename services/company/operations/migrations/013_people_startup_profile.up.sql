-- Migration 013: Backfill people profile to Project Startup Team
-- Bổ sung people profile dưới dạng TEMPLATE cho các Project hiện có chưa có people profile.

CREATE SEQUENCE IF NOT EXISTS operating.temp_assignment_id_seq START WITH 1000;
CREATE SEQUENCE IF NOT EXISTS operating.temp_assignment_event_id_seq START WITH 1000;

WITH inserted_assignments AS (
  INSERT INTO operating.project_agent_assignments (
    id,
    workspace_id,
    project_id,
    profile_key,
    state,
    disabled_reason,
    version,
    created_by,
    created_at,
    updated_at
  )
  SELECT
    (((extract(epoch from now()) * 1000)::bigint - 1704067200000) << 23) + nextval('operating.temp_assignment_id_seq'),
    p.workspace_id,
    p.id,
    'people',
    'TEMPLATE'::operating.project_agent_assignment_state,
    NULL,
    1,
    NULL,
    now(),
    now()
  FROM strategy.projects p
  ON CONFLICT (workspace_id, project_id, profile_key) DO NOTHING
  RETURNING id, workspace_id, project_id, profile_key
)
INSERT INTO operating.project_agent_assignment_events (
  id,
  workspace_id,
  project_id,
  assignment_id,
  event_type,
  from_state,
  to_state,
  assignment_version,
  actor_id,
  occurred_at,
  event_payload
)
SELECT
  (((extract(epoch from now()) * 1000)::bigint - 1704067200000) << 23) + nextval('operating.temp_assignment_event_id_seq'),
  ia.workspace_id,
  ia.project_id,
  ia.id,
  'ASSIGNMENT_TEMPLATE_CREATED',
  NULL,
  'TEMPLATE'::operating.project_agent_assignment_state,
  1,
  0,
  now(),
  jsonb_build_object(
    'profileKey', 'people',
    'source', 'people_profile_catalog_backfill_v1'
  )
FROM inserted_assignments ia;
