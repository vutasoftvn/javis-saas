-- services/company/finance-legal/migrations/30_ai_legal_source_corrections.down.sql

DROP TABLE IF EXISTS legal.ai_applicability_rules;

DELETE FROM legal.regulation_versions WHERE id >= 210 AND id <= 218;

UPDATE legal.regulation_versions
SET status = 'ACTIVE',
    correction_reason = NULL
WHERE id IN (110, 111, 112, 113, 114, 115, 116, 117);

ALTER TABLE legal.ai_compliance_evidence
  DROP COLUMN IF EXISTS conclusion,
  DROP COLUMN IF EXISTS source_version_ids,
  DROP COLUMN IF EXISTS rule_ids;

ALTER TABLE legal.regulation_versions
  DROP COLUMN IF EXISTS status,
  DROP COLUMN IF EXISTS content_hash,
  DROP COLUMN IF EXISTS correction_reason,
  DROP COLUMN IF EXISTS artifact_path,
  DROP COLUMN IF EXISTS reviewer_member_id,
  DROP COLUMN IF EXISTS reviewed_at;
