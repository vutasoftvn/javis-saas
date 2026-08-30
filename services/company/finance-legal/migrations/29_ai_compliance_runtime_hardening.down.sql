-- services/company/finance-legal/migrations/29_ai_compliance_runtime_hardening.down.sql
-- Rollback cho 29_ai_compliance_runtime_hardening.up.sql. Drop composite FK
-- trước (vì chúng phụ thuộc vào composite UNIQUE của bảng cha), sau đó drop
-- composite UNIQUE.

-- Rollback phần 3 (snapshot provenance columns) trước — drop FK rồi cột.
ALTER TABLE legal.ai_compliance_snapshots
  DROP CONSTRAINT IF EXISTS ai_compliance_snapshots_workspace_data_profile_fk;

ALTER TABLE legal.ai_compliance_snapshots
  DROP CONSTRAINT IF EXISTS ai_compliance_snapshots_workspace_provider_fk;

ALTER TABLE legal.ai_compliance_snapshots
  DROP COLUMN IF EXISTS provenance_complete,
  DROP COLUMN IF EXISTS data_profile_id,
  DROP COLUMN IF EXISTS provider_profile_id,
  DROP COLUMN IF EXISTS evidence_hashes,
  DROP COLUMN IF EXISTS evidence_ids,
  DROP COLUMN IF EXISTS capability_binding_ids;

ALTER TABLE legal.ai_data_processing_profiles
  DROP CONSTRAINT IF EXISTS ai_data_processing_profiles_workspace_id_id_key;

ALTER TABLE legal.ai_compliance_snapshots
  DROP CONSTRAINT IF EXISTS ai_compliance_snapshots_workspace_assessment_fk;

ALTER TABLE legal.ai_compliance_snapshots
  DROP CONSTRAINT IF EXISTS ai_compliance_snapshots_workspace_deployment_fk;

ALTER TABLE legal.ai_incident_actions
  DROP CONSTRAINT IF EXISTS ai_incident_actions_workspace_incident_fk;

ALTER TABLE legal.ai_incidents
  DROP CONSTRAINT IF EXISTS ai_incidents_workspace_deployment_fk;

ALTER TABLE legal.ai_data_processing_profiles
  DROP CONSTRAINT IF EXISTS ai_data_profiles_workspace_provider_fk;

ALTER TABLE legal.ai_data_processing_profiles
  DROP CONSTRAINT IF EXISTS ai_data_profiles_workspace_deployment_fk;

ALTER TABLE legal.ai_compliance_evidence
  DROP CONSTRAINT IF EXISTS ai_compliance_evidence_workspace_assessment_fk;

ALTER TABLE legal.workspace_ai_deployments
  DROP CONSTRAINT IF EXISTS workspace_ai_deployments_workspace_assessment_fk;

ALTER TABLE legal.ai_risk_assessments
  DROP CONSTRAINT IF EXISTS ai_risk_assessments_workspace_deployment_fk;

ALTER TABLE legal.ai_incidents
  DROP CONSTRAINT IF EXISTS ai_incidents_workspace_id_id_key;

ALTER TABLE legal.ai_provider_profiles
  DROP CONSTRAINT IF EXISTS ai_provider_profiles_workspace_id_id_key;

ALTER TABLE legal.ai_risk_assessments
  DROP CONSTRAINT IF EXISTS ai_risk_assessments_workspace_id_id_key;

ALTER TABLE legal.workspace_ai_deployments
  DROP CONSTRAINT IF EXISTS workspace_ai_deployments_workspace_id_id_key;
