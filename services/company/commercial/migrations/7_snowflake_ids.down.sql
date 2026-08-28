-- Rollback 7_snowflake_ids.up.sql
-- In reverse, tables can retain bigserial or no default (no-op rollback since IDs are app-generated)
SELECT 1;
