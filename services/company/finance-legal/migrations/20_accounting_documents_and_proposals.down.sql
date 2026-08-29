-- services/company/finance-legal/migrations/20_accounting_documents_and_proposals.down.sql
DROP INDEX IF EXISTS finance.idx_reconciliation_proposals_ws_status;
DROP TABLE IF EXISTS finance.document_reconciliation_proposals CASCADE;
DROP INDEX IF EXISTS finance.idx_accounting_documents_ws_date;
DROP INDEX IF EXISTS finance.idx_accounting_documents_ws_status;
DROP TABLE IF EXISTS finance.accounting_documents CASCADE;
