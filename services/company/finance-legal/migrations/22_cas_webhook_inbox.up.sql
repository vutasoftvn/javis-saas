-- services/company/finance-legal/migrations/22_cas_webhook_inbox.up.sql
CREATE TABLE IF NOT EXISTS finance.cas_webhook_inbox (
  id                BIGINT PRIMARY KEY,
  provider_event_id TEXT NOT NULL UNIQUE,
  raw_payload       TEXT NOT NULL,
  signature_header  TEXT,
  status            TEXT NOT NULL DEFAULT 'RECEIVED'
                      CHECK (status IN ('RECEIVED','PROCESSING','PROCESSED','FAILED','DLQ')),
  error_msg         TEXT,
  received_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_cas_webhook_inbox_status
  ON finance.cas_webhook_inbox(status, received_at);
