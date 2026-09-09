-- COSA Automation MVP (Task 1) — Control Plane dispatch fencing for automation
-- runs. Opaque references ONLY: invocation id, task id, claim token, version/hash,
-- trigger identity. No business content, prompt, credential or connector grant.
-- docs/superpowers/plans/2026-09-10-cosa-automation-mvp.md
--
-- Expand-only. Schema `control_plane` already exists (001 baseline + 002 restore).

CREATE TABLE IF NOT EXISTS control_plane.automation_dispatches (
  invocation_id  TEXT PRIMARY KEY,
  workspace_id   TEXT NOT NULL,
  automation_key TEXT NOT NULL,
  revision       INTEGER NOT NULL,
  revision_hash  TEXT NOT NULL,
  trigger_kind   TEXT NOT NULL,
  trigger_identity TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  task_id        TEXT,
  claim_token    TEXT,
  state          TEXT NOT NULL DEFAULT 'received'
                   CHECK (state IN ('received', 'scheduled', 'claimed', 'completed', 'failed', 'quarantined')),
  last_error     TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  scheduled_at   TIMESTAMPTZ,
  completed_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_automation_dispatches_state
  ON control_plane.automation_dispatches (state, created_at);
CREATE INDEX IF NOT EXISTS idx_automation_dispatches_task
  ON control_plane.automation_dispatches (task_id) WHERE task_id IS NOT NULL;
