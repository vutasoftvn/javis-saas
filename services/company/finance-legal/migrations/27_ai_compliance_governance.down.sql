-- services/company/finance-legal/migrations/27_ai_compliance_governance.down.sql
-- Drop AI compliance governance tables in reverse dependency order

DROP TABLE IF EXISTS legal.ai_compliance_snapshots CASCADE;
DROP TABLE IF EXISTS legal.ai_incident_actions CASCADE;
DROP TABLE IF EXISTS legal.ai_incidents CASCADE;
DROP TABLE IF EXISTS legal.data_subject_requests CASCADE;
DROP TABLE IF EXISTS legal.data_processing_authorizations CASCADE;
DROP TABLE IF EXISTS legal.ai_data_processing_profiles CASCADE;
DROP TABLE IF EXISTS legal.ai_provider_profiles CASCADE;
DROP TABLE IF EXISTS legal.ai_compliance_evidence CASCADE;

ALTER TABLE IF EXISTS legal.workspace_ai_deployments
  DROP CONSTRAINT IF EXISTS fk_workspace_ai_deployments_assessment;

DROP TABLE IF EXISTS legal.ai_risk_assessments CASCADE;
DROP TABLE IF EXISTS legal.ai_system_capability_bindings CASCADE;
DROP TABLE IF EXISTS legal.workspace_ai_deployments CASCADE;
DROP TABLE IF EXISTS legal.ai_system_versions CASCADE;
DROP TABLE IF EXISTS legal.ai_system_catalog CASCADE;
