-- 41_gate_decision_provenance.down.sql

ALTER TABLE strategy.project_stage_transitions
  DROP COLUMN IF EXISTS expected_stage_version,
  DROP COLUMN IF EXISTS decision_id,
  DROP COLUMN IF EXISTS provenance_snapshot;

ALTER TABLE strategy.workspace_stage_transitions
  DROP COLUMN IF EXISTS expected_stage_version,
  DROP COLUMN IF EXISTS decision_id,
  DROP COLUMN IF EXISTS provenance_snapshot;

ALTER TABLE strategy.gate_evaluations
  DROP COLUMN IF EXISTS expected_stage_version,
  DROP COLUMN IF EXISTS decision_id,
  DROP COLUMN IF EXISTS provenance_snapshot;
