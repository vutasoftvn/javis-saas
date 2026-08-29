-- services/company/finance-legal/migrations/24_reconciliation_accepted_by.up.sql
-- M1 §2 — reconciliation accept phải ghi ai chấp nhận (audit trail).
ALTER TABLE finance.document_reconciliation_proposals
  ADD COLUMN IF NOT EXISTS accepted_by BIGINT,
  ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMPTZ;
