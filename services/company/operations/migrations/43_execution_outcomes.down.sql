-- services/company/operations/migrations/43_execution_outcomes.down.sql

DROP TABLE IF EXISTS operating.kr_observations CASCADE;
DROP TABLE IF EXISTS operating.commitment_key_results CASCADE;
DROP TABLE IF EXISTS operating.cycle_key_results CASCADE;

ALTER TABLE operating.weekly_commitments
  DROP COLUMN IF EXISTS committed_at,
  DROP COLUMN IF EXISTS done_criteria,
  DROP COLUMN IF EXISTS purpose_ref,
  DROP COLUMN IF EXISTS purpose_type,
  DROP COLUMN IF EXISTS owner_member_id;

ALTER TABLE strategy.key_results
  DROP COLUMN IF EXISTS metric_contract_version,
  DROP COLUMN IF EXISTS scoring_type;
