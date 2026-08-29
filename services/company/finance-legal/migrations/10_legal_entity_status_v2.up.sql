-- services/company/finance-legal/migrations/10_legal_entity_status_v2.up.sql
-- M4 §5 — Legal entity status tách hẳn khỏi Workspace stage.
--   enum mới: DRAFT | REGISTRATION_PREPARATION | REGISTERED_UNVERIFIED | VERIFIED | SUSPENDED | DISSOLVED
--   (bỏ REGISTRATION_READINESS; có registration number ⇒ REGISTERED_UNVERIFIED trước khi verify)
--   drop legal_entity_profiles.platform_company_id.

-- Bỏ CHECK cũ (inline auto-named từ migration 13) trước khi backfill sang enum mới.
ALTER TABLE legal.legal_entity_profiles DROP CONSTRAINT IF EXISTS legal_entity_profiles_status_check;

UPDATE legal.legal_entity_profiles SET status = CASE status
  WHEN 'NOT_DECLARED'                    THEN 'DRAFT'
  WHEN 'UNREGISTERED'                    THEN 'DRAFT'
  WHEN 'REGISTRATION_READINESS'          THEN 'REGISTRATION_PREPARATION'
  WHEN 'REGISTERED_PENDING_VERIFICATION' THEN 'REGISTERED_UNVERIFIED'
  WHEN 'REGISTERED_VERIFIED'             THEN 'VERIFIED'
  ELSE status
END;

UPDATE legal.legal_verification_approvals
  SET expected_status = 'VERIFIED'
  WHERE expected_status = 'REGISTERED_VERIFIED';

ALTER TABLE legal.legal_entity_profiles ALTER COLUMN status SET DEFAULT 'DRAFT';
ALTER TABLE legal.legal_entity_profiles
  ADD CONSTRAINT legal_entity_profiles_status_chk
  CHECK (status IN (
    'DRAFT', 'REGISTRATION_PREPARATION', 'REGISTERED_UNVERIFIED',
    'VERIFIED', 'SUSPENDED', 'DISSOLVED'
  ));

ALTER TABLE legal.legal_entity_profiles DROP COLUMN IF EXISTS platform_company_id;
