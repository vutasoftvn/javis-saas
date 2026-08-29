-- services/company/operations/migrations/25_workspace_stage_transition_cas.up.sql
-- M4 §2 — versioned transition policy + evidence/eval snapshot + CAS metadata trong journal.

ALTER TABLE strategy.stage_transition_policies
  ADD COLUMN IF NOT EXISTS policy_version TEXT NOT NULL DEFAULT 'v1';

ALTER TABLE strategy.workspace_stage_transitions
  ADD COLUMN IF NOT EXISTS stage_version_from    INTEGER,
  ADD COLUMN IF NOT EXISTS source                TEXT NOT NULL DEFAULT 'manual',
  ADD COLUMN IF NOT EXISTS actor_role            TEXT,
  ADD COLUMN IF NOT EXISTS policy_version        TEXT,
  ADD COLUMN IF NOT EXISTS override_approval_ref TEXT,
  ADD COLUMN IF NOT EXISTS evidence_snapshot     JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS evaluation_result     JSONB;

ALTER TABLE strategy.workspace_stage_transitions
  ADD CONSTRAINT workspace_stage_transitions_source_chk
  CHECK (source IN ('manual', 'autonomous', 'api', 'system'));
