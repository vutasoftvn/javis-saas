-- services/company/finance-legal/migrations/28_ai_compliance_legal_sources.down.sql
-- Remove seeded AI compliance regulation sources and versions

DELETE FROM legal.regulation_versions WHERE id IN (110, 111, 112, 113, 114, 115, 116, 117);
DELETE FROM legal.regulation_sources WHERE id IN (10, 11, 12, 13, 14, 15, 16, 17);
