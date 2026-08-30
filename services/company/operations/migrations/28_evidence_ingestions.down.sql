-- services/company/operations/migrations/28_evidence_ingestions.down.sql

ALTER TABLE strategy.evidence
  DROP COLUMN IF EXISTS fresh_until,
  DROP COLUMN IF EXISTS observed_at,
  DROP COLUMN IF EXISTS fact_or_inference,
  DROP COLUMN IF EXISTS source_system,
  DROP COLUMN IF EXISTS source_url,
  DROP COLUMN IF EXISTS artifact_ref,
  DROP COLUMN IF EXISTS evidence_ingestion_id;

DROP INDEX IF EXISTS strategy.idx_evidence_ingestions_ws_proj;
DROP INDEX IF EXISTS strategy.uq_evidence_ingestions_source_hash;
DROP TABLE IF EXISTS strategy.evidence_ingestions;
