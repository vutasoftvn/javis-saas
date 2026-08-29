-- services/company/operations/migrations/20_decision_records.down.sql
DROP INDEX IF EXISTS strategy.idx_decision_records_workspace_type_created;

ALTER TABLE strategy.decision_records
  DROP COLUMN IF EXISTS decided_at,
  DROP COLUMN IF EXISTS founder_decision,
  DROP COLUMN IF EXISTS ai_prompt_version,
  DROP COLUMN IF EXISTS policy_version,
  DROP COLUMN IF EXISTS alternatives,
  DROP COLUMN IF EXISTS assumptions,
  DROP COLUMN IF EXISTS confidence,
  DROP COLUMN IF EXISTS regulation_refs,
  DROP COLUMN IF EXISTS evidence_refs,
  DROP COLUMN IF EXISTS created_by_ref,
  DROP COLUMN IF EXISTS created_by_kind,
  DROP COLUMN IF EXISTS decision_type;
