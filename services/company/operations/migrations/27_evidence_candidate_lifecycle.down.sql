-- services/company/operations/migrations/27_evidence_candidate_lifecycle.down.sql
DROP INDEX IF EXISTS strategy.idx_evidence_ws_proj_status;
ALTER TABLE strategy.evidence
  DROP COLUMN IF EXISTS reviewed_at,
  DROP COLUMN IF EXISTS reviewed_by_member_id,
  DROP COLUMN IF EXISTS review_comment,
  DROP COLUMN IF EXISTS status;
