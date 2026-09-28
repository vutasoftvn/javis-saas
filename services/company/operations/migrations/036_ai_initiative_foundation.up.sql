-- Migration 036: AI Initiative Foundation and Project Scoping

ALTER TABLE strategy.initiatives
  ADD COLUMN IF NOT EXISTS initiative_kind TEXT NOT NULL DEFAULT 'GENERIC',
  ADD COLUMN IF NOT EXISTS lifecycle_state TEXT NOT NULL DEFAULT 'DISCOVER',
  ADD COLUMN IF NOT EXISTS risk_tier TEXT NOT NULL DEFAULT 'LOW',
  ADD COLUMN IF NOT EXISTS autonomy_tier TEXT NOT NULL DEFAULT 'A0',
  ADD COLUMN IF NOT EXISTS business_problem TEXT,
  ADD COLUMN IF NOT EXISTS technical_owner_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS risk_owner_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS legacy_remediation_state TEXT NOT NULL DEFAULT 'CLEAN';

-- Guarded constraints
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_initiatives_initiative_kind'
  ) THEN
    ALTER TABLE strategy.initiatives
      ADD CONSTRAINT chk_initiatives_initiative_kind
      CHECK (initiative_kind IN ('GENERIC', 'AI'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_initiatives_lifecycle_state'
  ) THEN
    ALTER TABLE strategy.initiatives
      ADD CONSTRAINT chk_initiatives_lifecycle_state
      CHECK (lifecycle_state IN ('DISCOVER', 'PILOT', 'VALIDATE', 'SCALE_CANDIDATE', 'SCALED', 'PAUSED', 'RETIRED'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_initiatives_risk_tier'
  ) THEN
    ALTER TABLE strategy.initiatives
      ADD CONSTRAINT chk_initiatives_risk_tier
      CHECK (risk_tier IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_initiatives_autonomy_tier'
  ) THEN
    ALTER TABLE strategy.initiatives
      ADD CONSTRAINT chk_initiatives_autonomy_tier
      CHECK (autonomy_tier IN ('A0', 'A1', 'A2', 'A3'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_initiatives_legacy_remediation_state'
  ) THEN
    ALTER TABLE strategy.initiatives
      ADD CONSTRAINT chk_initiatives_legacy_remediation_state
      CHECK (legacy_remediation_state IN ('CLEAN', 'NEEDS_REBIND'));
  END IF;
END $$;

-- Foreign key constraints for owners
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_initiatives_technical_owner'
  ) THEN
    ALTER TABLE strategy.initiatives
      ADD CONSTRAINT fk_initiatives_technical_owner
      FOREIGN KEY (technical_owner_member_id)
      REFERENCES core.workforce_members(id)
      ON DELETE SET NULL;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_initiatives_risk_owner'
  ) THEN
    ALTER TABLE strategy.initiatives
      ADD CONSTRAINT fk_initiatives_risk_owner
      FOREIGN KEY (risk_owner_member_id)
      REFERENCES core.workforce_members(id)
      ON DELETE SET NULL;
  END IF;
END $$;

-- Composite & Foreign key indexes
CREATE INDEX IF NOT EXISTS idx_initiatives_ws_proj_lifecycle_updated
  ON strategy.initiatives(workspace_id, project_id, lifecycle_state, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_initiatives_technical_owner
  ON strategy.initiatives(technical_owner_member_id);

CREATE INDEX IF NOT EXISTS idx_initiatives_risk_owner
  ON strategy.initiatives(risk_owner_member_id);

-- Mark preexisting rows with missing project/KR references as NEEDS_REBIND
UPDATE strategy.initiatives
SET legacy_remediation_state = 'NEEDS_REBIND'
WHERE project_id IS NULL OR key_result_id IS NULL;
