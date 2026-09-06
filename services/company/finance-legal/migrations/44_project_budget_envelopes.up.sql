-- Migration 44: F6a — project budget envelopes + payment-request override audit
-- (docs/superpowers/specs/2026-09-06-f6a-budget-summary-design.md)

CREATE TABLE finance.project_budget_envelopes (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  legal_entity_id BIGINT NOT NULL,
  currency VARCHAR(10) NOT NULL DEFAULT 'VND',
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  limit_minor NUMERIC(38, 0) NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  owner_member_id BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_budget_envelopes_project
  ON finance.project_budget_envelopes(project_id, period_start, period_end);

ALTER TABLE finance.payment_requests
  ADD COLUMN IF NOT EXISTS budget_override_reason TEXT,
  ADD COLUMN IF NOT EXISTS budget_override_by_member_id BIGINT;
