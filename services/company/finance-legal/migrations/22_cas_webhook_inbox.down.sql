-- services/company/finance-legal/migrations/22_cas_webhook_inbox.down.sql
DROP INDEX IF EXISTS finance.idx_cas_webhook_inbox_status;
DROP TABLE IF EXISTS finance.cas_webhook_inbox CASCADE;
