-- services/company/finance-legal/migrations/20_accounting_documents_and_proposals.up.sql
CREATE TABLE IF NOT EXISTS finance.accounting_documents (
  id                BIGINT PRIMARY KEY,
  workspace_id      BIGINT NOT NULL,
  document_type     TEXT NOT NULL CHECK (document_type IN ('RECEIPT','PAYMENT','INVOICE','JOURNAL')),
  number            TEXT NOT NULL,
  document_date     DATE NOT NULL,
  amount            NUMERIC(20, 2) NOT NULL,
  currency          TEXT NOT NULL DEFAULT 'VND',
  description       TEXT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'DRAFT'
                      CHECK (status IN ('DRAFT','CONFIRMED','VOID')),
  regime_policy_id  BIGINT REFERENCES finance.accounting_regime_policies(id) ON DELETE SET NULL,
  line_items        JSONB NOT NULL DEFAULT '[]'::jsonb,
  confirmed_at      TIMESTAMPTZ,
  confirmed_by      BIGINT,
  void_reason       TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, number)
);

CREATE INDEX IF NOT EXISTS idx_accounting_documents_ws_status
  ON finance.accounting_documents(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_accounting_documents_ws_date
  ON finance.accounting_documents(workspace_id, document_date);

CREATE TABLE IF NOT EXISTS finance.document_reconciliation_proposals (
  id                      BIGINT PRIMARY KEY,
  workspace_id            BIGINT NOT NULL,
  bank_transaction_id     BIGINT NOT NULL REFERENCES finance.bank_transactions(id) ON DELETE CASCADE,
  accounting_document_id  BIGINT NOT NULL REFERENCES finance.accounting_documents(id) ON DELETE CASCADE,
  confidence              NUMERIC(5, 4) NOT NULL,
  candidate_match         JSONB NOT NULL DEFAULT '{}'::jsonb,
  status                  TEXT NOT NULL DEFAULT 'PENDING'
                            CHECK (status IN ('PENDING','ACCEPTED','REJECTED')),
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_proposals_ws_status
  ON finance.document_reconciliation_proposals(workspace_id, status);
