CREATE TABLE finance.finance_management_snapshots (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  cycle_id BIGINT,
  as_of DATE NOT NULL,
  cash NUMERIC(20, 2) NOT NULL,
  burn NUMERIC(20, 2) NOT NULL,
  runway_months NUMERIC(12, 2),
  revenue NUMERIC(20, 2) NOT NULL DEFAULT 0,
  expenses NUMERIC(20, 2) NOT NULL DEFAULT 0,
  budget_variance NUMERIC(20, 2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_finance_snapshots_workspace_id ON finance.finance_management_snapshots(workspace_id);
CREATE INDEX idx_finance_snapshots_workspace_as_of ON finance.finance_management_snapshots(workspace_id, as_of DESC);
