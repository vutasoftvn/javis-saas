CREATE TABLE finance.financial_transactions (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  document_id BIGINT,
  project_id BIGINT,
  cycle_id BIGINT,
  work_item_id BIGINT,
  transaction_date DATE NOT NULL,
  description TEXT NOT NULL,
  amount NUMERIC(20, 2) NOT NULL,
  direction TEXT NOT NULL,
  category TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_financial_transactions_workspace_id ON finance.financial_transactions(workspace_id);

CREATE TABLE finance.finance_exceptions (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  transaction_id BIGINT REFERENCES finance.financial_transactions(id) ON DELETE CASCADE,
  exception_type TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'WARNING',
  details JSONB,
  status TEXT NOT NULL DEFAULT 'OPEN',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_finance_exceptions_workspace_id ON finance.finance_exceptions(workspace_id);
CREATE INDEX idx_finance_exceptions_transaction_id ON finance.finance_exceptions(transaction_id);
