-- Rollback 1_create_accounts_contacts.up.sql
DROP TABLE IF EXISTS sales.contacts CASCADE;
DROP TABLE IF EXISTS sales.accounts CASCADE;
