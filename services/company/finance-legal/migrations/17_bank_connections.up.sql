-- services/company/finance-legal/migrations/17_bank_connections.up.sql
CREATE TABLE IF NOT EXISTS finance.bank_connections (
  id                BIGINT PRIMARY KEY,
  workspace_id      BIGINT NOT NULL,
  provider          TEXT NOT NULL CHECK (provider IN ('cas','manual')),
  consent_state     TEXT NOT NULL DEFAULT 'PENDING'
                      CHECK (consent_state IN ('PENDING','GRANTED','REVOKED','EXPIRED')),
  secret_ref        TEXT CHECK (secret_ref IS NULL OR secret_ref LIKE 'secret://cosa-connectors/%'),
  scopes            JSONB NOT NULL DEFAULT '[]'::jsonb,
  account_links     JSONB NOT NULL DEFAULT '[]'::jsonb,
  grant_expires_at  TIMESTAMPTZ,
  last_synced_at    TIMESTAMPTZ,
  sync_status       TEXT NOT NULL DEFAULT 'IDLE',
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bank_connections_ws_provider
  ON finance.bank_connections(workspace_id, provider);
