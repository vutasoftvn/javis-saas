-- services/company/finance-legal/migrations/18_ingestion_events.up.sql
CREATE TABLE IF NOT EXISTS finance.ingestion_events (
  id                  BIGINT PRIMARY KEY,
  bank_connection_id  BIGINT NOT NULL REFERENCES finance.bank_connections(id) ON DELETE CASCADE,
  provider_event_id   TEXT NOT NULL,
  received_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw_payload_ref     TEXT,
  checksum            TEXT,
  status              TEXT NOT NULL DEFAULT 'RECEIVED'
                        CHECK (status IN ('RECEIVED','PROCESSING','PROCESSED','FAILED','DLQ')),
  error_msg           TEXT,
  processed_at        TIMESTAMPTZ,
  UNIQUE (bank_connection_id, provider_event_id)
);

CREATE INDEX IF NOT EXISTS idx_ingestion_events_status_received
  ON finance.ingestion_events(status, received_at);
