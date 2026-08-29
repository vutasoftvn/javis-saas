-- services/company/finance-legal/migrations/13_legal_applicability_obligations.down.sql
DROP INDEX IF EXISTS legal.idx_legal_obligation_instances_workspace_due;
DROP INDEX IF EXISTS legal.idx_legal_obligation_instances_workspace_status;
DROP TABLE IF EXISTS legal.legal_obligation_instances CASCADE;
DROP TABLE IF EXISTS legal.applicability_rules CASCADE;
DROP TABLE IF EXISTS legal.legal_obligation_templates CASCADE;
DROP INDEX IF EXISTS legal.idx_legal_entity_profiles_workspace;
DROP TABLE IF EXISTS legal.legal_entity_profiles CASCADE;
