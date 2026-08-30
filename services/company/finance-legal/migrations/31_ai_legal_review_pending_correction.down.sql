-- services/company/finance-legal/migrations/31_ai_legal_review_pending_correction.down.sql

UPDATE legal.ai_applicability_rules
SET review_status = 'REVIEWED',
    updated_at = now()
WHERE id IN (301, 302, 303, 304, 305, 306);

ALTER TABLE legal.regulation_versions
  DROP COLUMN IF EXISTS legal_review_confirmed;
