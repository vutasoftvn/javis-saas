CREATE SCHEMA IF NOT EXISTS finance;

CREATE TABLE finance.accounting_profiles (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'TT58_MODE_1',
  status TEXT NOT NULL DEFAULT 'DRAFT',
  confirmed_by BIGINT,
  confirmed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id)
);

CREATE TABLE finance.accounting_periods (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  closed_by BIGINT,
  closed_at TIMESTAMPTZ
);

CREATE INDEX idx_accounting_periods_workspace_id ON finance.accounting_periods(workspace_id);
