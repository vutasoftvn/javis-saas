-- services/company/finance-legal/migrations/24_reconciliation_accepted_by.down.sql
ALTER TABLE finance.document_reconciliation_proposals
  DROP COLUMN IF EXISTS accepted_by,
  DROP COLUMN IF EXISTS accepted_at;
