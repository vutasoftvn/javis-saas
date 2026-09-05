-- 41_gate_decision_provenance.up.sql
-- Thêm provenance snapshot, decision linkage và expected stage version cho Gate và Stage Transitions

ALTER TABLE strategy.gate_evaluations
  ADD COLUMN IF NOT EXISTS provenance_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL,
  ADD COLUMN IF NOT EXISTS decision_id BIGINT,
  ADD COLUMN IF NOT EXISTS expected_stage_version INTEGER;

ALTER TABLE strategy.workspace_stage_transitions
  ADD COLUMN IF NOT EXISTS provenance_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL,
  ADD COLUMN IF NOT EXISTS decision_id BIGINT,
  ADD COLUMN IF NOT EXISTS expected_stage_version INTEGER;

ALTER TABLE strategy.project_stage_transitions
  ADD COLUMN IF NOT EXISTS provenance_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL,
  ADD COLUMN IF NOT EXISTS decision_id BIGINT,
  ADD COLUMN IF NOT EXISTS expected_stage_version INTEGER;
