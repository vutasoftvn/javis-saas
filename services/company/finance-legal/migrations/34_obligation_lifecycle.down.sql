DROP TABLE IF EXISTS legal.obligation_transitions;
DROP INDEX IF EXISTS legal.uq_legal_obligation_period_entity;
ALTER TABLE legal.legal_obligation_instances
  DROP COLUMN IF EXISTS evidence_refs,
  DROP COLUMN IF EXISTS period_key;
