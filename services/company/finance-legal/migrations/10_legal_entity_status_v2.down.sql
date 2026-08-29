-- Revert M4 §5.

ALTER TABLE legal.legal_entity_profiles ADD COLUMN IF NOT EXISTS platform_company_id TEXT;

ALTER TABLE legal.legal_entity_profiles DROP CONSTRAINT IF EXISTS legal_entity_profiles_status_chk;

UPDATE legal.legal_verification_approvals
  SET expected_status = 'REGISTERED_VERIFIED'
  WHERE expected_status = 'VERIFIED';

UPDATE legal.legal_entity_profiles SET status = CASE status
  WHEN 'DRAFT'                    THEN 'UNREGISTERED'
  WHEN 'REGISTRATION_PREPARATION' THEN 'REGISTRATION_READINESS'
  WHEN 'REGISTERED_UNVERIFIED'    THEN 'REGISTERED_PENDING_VERIFICATION'
  WHEN 'VERIFIED'                 THEN 'REGISTERED_VERIFIED'
  ELSE status
END;

ALTER TABLE legal.legal_entity_profiles ALTER COLUMN status SET DEFAULT 'NOT_DECLARED';
ALTER TABLE legal.legal_entity_profiles
  ADD CONSTRAINT legal_entity_profiles_status_check
  CHECK (status IN (
    'NOT_DECLARED','UNREGISTERED','REGISTRATION_READINESS',
    'REGISTERED_PENDING_VERIFICATION','REGISTERED_VERIFIED'
  ));
