-- services/company/operations/migrations/20_decision_records.up.sql
-- Extend strategy.decision_records with workspace-level audit columns

ALTER TABLE strategy.decision_records
  ALTER COLUMN project_id DROP NOT NULL,
  ADD COLUMN IF NOT EXISTS decision_type TEXT,
  ADD COLUMN IF NOT EXISTS created_by_kind TEXT CHECK (created_by_kind IN ('FOUNDER','AI','SYSTEM')),
  ADD COLUMN IF NOT EXISTS created_by_ref TEXT,
  ADD COLUMN IF NOT EXISTS evidence_refs JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS regulation_refs JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS confidence NUMERIC,
  ADD COLUMN IF NOT EXISTS assumptions JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS alternatives JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS policy_version TEXT,
  ADD COLUMN IF NOT EXISTS ai_prompt_version TEXT,
  ADD COLUMN IF NOT EXISTS founder_decision TEXT CHECK (founder_decision IN ('accepted','rejected','deferred')),
  ADD COLUMN IF NOT EXISTS decided_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_decision_records_workspace_type_created
  ON strategy.decision_records(workspace_id, decision_type, created_at);
