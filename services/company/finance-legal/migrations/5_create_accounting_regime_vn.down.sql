-- Rollback 5_create_accounting_regime_vn.up.sql
DROP TABLE IF EXISTS finance.accounting_regime_transition_logs CASCADE;
DROP TABLE IF EXISTS finance.accounting_coa_mappings CASCADE;
DROP TABLE IF EXISTS finance.accounting_fiscal_profiles CASCADE;
