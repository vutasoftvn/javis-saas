-- services/company/finance-legal/migrations/12_legal_catalog.down.sql
DROP INDEX IF EXISTS legal.idx_regulation_versions_source_effective;
DROP TABLE IF EXISTS legal.regulation_versions CASCADE;
DROP TABLE IF EXISTS legal.regulation_sources CASCADE;
