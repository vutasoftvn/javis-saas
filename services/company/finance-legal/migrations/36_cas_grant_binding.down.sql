-- Migration 36 down: Revert Cas grant binding

DROP INDEX IF EXISTS finance.idx_cas_link_sessions_state_hash;
DROP INDEX IF EXISTS finance.idx_cas_link_sessions_ws;
DROP TABLE IF EXISTS finance.cas_link_sessions CASCADE;
DROP INDEX IF EXISTS finance.idx_bank_connections_provider_account_unique;

ALTER TABLE finance.bank_connections
  DROP COLUMN IF EXISTS reauth_required,
  DROP COLUMN IF EXISTS provider_contract_version,
  DROP COLUMN IF EXISTS grant_expires_at_v2,
  DROP COLUMN IF EXISTS granted_scopes,
  DROP COLUMN IF EXISTS account_fingerprint,
  DROP COLUMN IF EXISTS institution_id,
  DROP COLUMN IF EXISTS external_account_id,
  DROP COLUMN IF EXISTS provider_grant_id,
  DROP COLUMN IF EXISTS provider_environment,
  DROP COLUMN IF EXISTS legal_entity_id;
