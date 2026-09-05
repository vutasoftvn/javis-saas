-- Migration 36: Cas grant binding — legalEntityId, grant lifecycle, link sessions
-- F2: Connect Cas bank accounts with scoped grant lifecycle

-- Bổ sung các cột vào bank_connections cho F2
ALTER TABLE finance.bank_connections
  ADD COLUMN IF NOT EXISTS legal_entity_id BIGINT,
  ADD COLUMN IF NOT EXISTS provider_environment TEXT NOT NULL DEFAULT 'sandbox',
  ADD COLUMN IF NOT EXISTS provider_grant_id TEXT,
  ADD COLUMN IF NOT EXISTS external_account_id TEXT,
  ADD COLUMN IF NOT EXISTS institution_id TEXT,
  ADD COLUMN IF NOT EXISTS account_fingerprint TEXT,
  ADD COLUMN IF NOT EXISTS granted_scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS grant_expires_at_v2 TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS provider_contract_version TEXT,
  ADD COLUMN IF NOT EXISTS reauth_required BOOLEAN NOT NULL DEFAULT false;

-- Unique: cùng provider + environment + grant_id + external_account_id không thể map hai tenant
-- Grant_id một grant có thể nhiều account nên không unique trên grant_id đơn
CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_connections_provider_account_unique
  ON finance.bank_connections (provider, provider_environment, provider_grant_id, external_account_id)
  WHERE provider_grant_id IS NOT NULL AND external_account_id IS NOT NULL AND consent_state != 'REVOKED';

-- Link sessions cho OAuth redirect flow
CREATE TABLE IF NOT EXISTS finance.cas_link_sessions (
  id                  BIGINT PRIMARY KEY,
  workspace_id        BIGINT NOT NULL,
  legal_entity_id     BIGINT,
  created_by          BIGINT NOT NULL,
  state_hash          TEXT NOT NULL UNIQUE,
  scopes              JSONB NOT NULL DEFAULT '[]'::jsonb,
  allowed_redirect    TEXT NOT NULL,
  expires_at          TIMESTAMPTZ NOT NULL,
  consumed_at         TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cas_link_sessions_ws
  ON finance.cas_link_sessions (workspace_id);

CREATE INDEX IF NOT EXISTS idx_cas_link_sessions_state_hash
  ON finance.cas_link_sessions (state_hash)
  WHERE consumed_at IS NULL;
