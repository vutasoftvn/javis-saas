-- services/company/operations/migrations/27_evidence_candidate_lifecycle.up.sql
-- Evidence Kernel: candidate-to-approved lifecycle & privileged review
ALTER TABLE strategy.evidence
  ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'candidate',
  ADD COLUMN IF NOT EXISTS review_comment TEXT,
  ADD COLUMN IF NOT EXISTS reviewed_by_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_evidence_ws_proj_status
  ON strategy.evidence(workspace_id, project_id, status);
