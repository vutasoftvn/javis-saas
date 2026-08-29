-- services/company/finance-legal/migrations/19_bank_transactions.up.sql
CREATE TABLE IF NOT EXISTS finance.bank_transactions (
  id                              BIGINT PRIMARY KEY,
  workspace_id                    BIGINT NOT NULL,
  bank_connection_id              BIGINT NOT NULL REFERENCES finance.bank_connections(id) ON DELETE CASCADE,
  ingestion_event_id              BIGINT REFERENCES finance.ingestion_events(id) ON DELETE SET NULL,
  external_transaction_id         TEXT NOT NULL,
  posted_at                       TIMESTAMPTZ NOT NULL,
  amount                          NUMERIC(20, 2) NOT NULL,
  currency                        TEXT NOT NULL DEFAULT 'VND',
  direction                       TEXT NOT NULL CHECK (direction IN ('IN','OUT')),
  description                     TEXT NOT NULL,
  counterparty_name               TEXT,
  counterparty_account            TEXT,
  status                          TEXT NOT NULL DEFAULT 'UNRECONCILED'
                                    CHECK (status IN ('UNRECONCILED','MATCHED','CONFIRMED')),
  matched_accounting_document_id  BIGINT,
  raw_payload                     JSONB,
  created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (bank_connection_id, external_transaction_id)
);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_ws_status
  ON finance.bank_transactions(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_ws_posted
  ON finance.bank_transactions(workspace_id, posted_at);
