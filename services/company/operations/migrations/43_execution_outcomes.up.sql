-- services/company/operations/migrations/43_execution_outcomes.up.sql
-- S3: Linking weekly commitments to measured outcomes, KR observations, and evidence

-- Key results scoring configuration
ALTER TABLE strategy.key_results
  ADD COLUMN IF NOT EXISTS scoring_type VARCHAR(50) NOT NULL DEFAULT 'LINEAR_INCREASE',
  ADD COLUMN IF NOT EXISTS metric_contract_version INTEGER NULL;

-- Commitments purpose, owner, and completion criteria
ALTER TABLE operating.weekly_commitments
  ADD COLUMN IF NOT EXISTS owner_member_id BIGINT NULL,
  ADD COLUMN IF NOT EXISTS purpose_type VARCHAR(50) NOT NULL DEFAULT 'KR',
  ADD COLUMN IF NOT EXISTS purpose_ref TEXT NULL,
  ADD COLUMN IF NOT EXISTS done_criteria JSONB NULL,
  ADD COLUMN IF NOT EXISTS committed_at TIMESTAMPTZ NULL;

-- Cycle to Key Results link (a single KR can span multiple cycles without duplicating observation progress)
CREATE TABLE IF NOT EXISTS operating.cycle_key_results (
  workspace_id BIGINT NOT NULL,
  cycle_id BIGINT NOT NULL REFERENCES operating.twelve_week_cycles(id) ON DELETE CASCADE,
  key_result_id BIGINT NOT NULL REFERENCES strategy.key_results(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, cycle_id, key_result_id)
);

-- Commitment to Key Results link (a task/commitment can contribute to multiple KRs)
CREATE TABLE IF NOT EXISTS operating.commitment_key_results (
  workspace_id BIGINT NOT NULL,
  commitment_id BIGINT NOT NULL REFERENCES operating.weekly_commitments(id) ON DELETE CASCADE,
  key_result_id BIGINT NOT NULL REFERENCES strategy.key_results(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, commitment_id, key_result_id)
);

-- Append-only KR observations
CREATE TABLE IF NOT EXISTS operating.kr_observations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id BIGINT NOT NULL,
  kr_id BIGINT NOT NULL REFERENCES strategy.key_results(id) ON DELETE CASCADE,
  value_decimal NUMERIC(18, 4) NOT NULL,
  measurement_at TIMESTAMPTZ NOT NULL,
  window_start TIMESTAMPTZ NULL,
  window_end TIMESTAMPTZ NULL,
  evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  source_ref TEXT NULL,
  recorded_by BIGINT NULL,
  metric_contract_version INTEGER NULL,
  idempotency_key TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uix_kr_observations_ws_kr_idempotency
  ON operating.kr_observations(workspace_id, kr_id, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_kr_observations_kr_measurement
  ON operating.kr_observations(workspace_id, kr_id, measurement_at DESC);
