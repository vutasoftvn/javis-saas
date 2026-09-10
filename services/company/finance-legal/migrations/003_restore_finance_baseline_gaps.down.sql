-- Rollback Task 5C — bỏ 20 bảng `finance.*` mà `003_restore_finance_baseline_gaps.up.sql`
-- tạo lại. Thứ tự đảo phụ thuộc (bảng con trước bảng cha); CASCADE để dọn luôn
-- index / constraint / FK phụ thuộc.

DROP TABLE IF EXISTS finance.payment_allocations CASCADE;
DROP TABLE IF EXISTS finance.payment_requests CASCADE;
DROP TABLE IF EXISTS finance.ingestion_events CASCADE;
DROP TABLE IF EXISTS finance.ingestion_dlq CASCADE;
DROP TABLE IF EXISTS finance.finance_management_snapshots CASCADE;
DROP TABLE IF EXISTS finance.document_reconciliation_proposals CASCADE;
DROP TABLE IF EXISTS finance.cas_normalizer_log CASCADE;
DROP TABLE IF EXISTS finance.tax_obligation_instances CASCADE;
DROP TABLE IF EXISTS finance.accounting_report_mappings CASCADE;
DROP TABLE IF EXISTS finance.accounting_regime_transition_logs CASCADE;
DROP TABLE IF EXISTS finance.accounting_profiles CASCADE;
DROP TABLE IF EXISTS finance.accounting_policies CASCADE;
DROP TABLE IF EXISTS finance.accounting_mapping_confirmations CASCADE;
DROP TABLE IF EXISTS finance.accounting_coa_mappings CASCADE;
DROP TABLE IF EXISTS finance.accounting_report_snapshots CASCADE;
DROP TABLE IF EXISTS finance.accounting_book_entries CASCADE;
DROP TABLE IF EXISTS finance.accounting_documents CASCADE;
DROP TABLE IF EXISTS finance.accounting_regime_policies CASCADE;
DROP TABLE IF EXISTS finance.accounting_periods CASCADE;
DROP TABLE IF EXISTS finance.accounting_fiscal_profiles CASCADE;
