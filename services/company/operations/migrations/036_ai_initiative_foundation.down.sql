-- Revert 036_ai_initiative_foundation
DROP INDEX IF EXISTS strategy.idx_initiatives_ws_proj_lifecycle_updated;
DROP INDEX IF EXISTS strategy.idx_initiatives_technical_owner;
DROP INDEX IF EXISTS strategy.idx_initiatives_risk_owner;

ALTER TABLE strategy.initiatives
  DROP CONSTRAINT IF EXISTS chk_initiatives_initiative_kind,
  DROP CONSTRAINT IF EXISTS chk_initiatives_lifecycle_state,
  DROP CONSTRAINT IF EXISTS chk_initiatives_risk_tier,
  DROP CONSTRAINT IF EXISTS chk_initiatives_autonomy_tier,
  DROP CONSTRAINT IF EXISTS chk_initiatives_legacy_remediation_state,
  DROP CONSTRAINT IF EXISTS fk_initiatives_technical_owner,
  DROP CONSTRAINT IF EXISTS fk_initiatives_risk_owner;

ALTER TABLE strategy.initiatives
  DROP COLUMN IF EXISTS initiative_kind,
  DROP COLUMN IF EXISTS lifecycle_state,
  DROP COLUMN IF EXISTS risk_tier,
  DROP COLUMN IF EXISTS autonomy_tier,
  DROP COLUMN IF EXISTS business_problem,
  DROP COLUMN IF EXISTS technical_owner_member_id,
  DROP COLUMN IF EXISTS risk_owner_member_id,
  DROP COLUMN IF EXISTS legacy_remediation_state;
