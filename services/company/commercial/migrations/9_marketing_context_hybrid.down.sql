-- Rollback 9_marketing_context_hybrid.up.sql
DROP TABLE IF EXISTS commercial.marketing_context_evidence CASCADE;
DROP TABLE IF EXISTS commercial.marketing_customer_language CASCADE;
DROP TABLE IF EXISTS commercial.marketing_customer_research_themes CASCADE;
DROP TABLE IF EXISTS commercial.marketing_icp_segments CASCADE;
DROP TABLE IF EXISTS commercial.marketing_product_marketing CASCADE;
DROP TABLE IF EXISTS commercial.marketing_context_revisions CASCADE;

ALTER TABLE commercial.marketing_contexts
  DROP CONSTRAINT IF EXISTS uix_marketing_contexts_workspace;

ALTER TABLE commercial.marketing_contexts
  DROP COLUMN IF EXISTS twelve_week_plan,
  DROP COLUMN IF EXISTS offer_architecture,
  DROP COLUMN IF EXISTS source_skill_hash,
  DROP COLUMN IF EXISTS source_skill_version,
  DROP COLUMN IF EXISTS source_skill_id,
  DROP COLUMN IF EXISTS reviewed_at,
  DROP COLUMN IF EXISTS reviewed_by_user_id,
  DROP COLUMN IF EXISTS updated_by_user_id,
  DROP COLUMN IF EXISTS status,
  DROP COLUMN IF EXISTS revision;
