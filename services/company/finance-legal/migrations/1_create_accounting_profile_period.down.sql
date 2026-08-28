-- Rollback 1_create_accounting_profile_period.up.sql
DROP TABLE IF EXISTS finance.accounting_periods CASCADE;
DROP TABLE IF EXISTS finance.accounting_profiles CASCADE;
