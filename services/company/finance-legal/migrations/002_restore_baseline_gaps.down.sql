-- Rollback 002_restore_baseline_gaps.up.sql — drop theo thứ tự con trước cha
-- (CASCADE dọn nốt index/constraint/composite FK còn sót). KHÔNG drop schema
-- legal (có thể còn bảng khác) và KHÔNG đụng bất cứ gì do 001 baseline tạo.
DROP TABLE IF EXISTS legal.ai_applicability_rules CASCADE;
DROP TABLE IF EXISTS legal.ai_compliance_snapshots CASCADE;
DROP TABLE IF EXISTS legal.ai_incident_actions CASCADE;
DROP TABLE IF EXISTS legal.ai_incidents CASCADE;
DROP TABLE IF EXISTS legal.data_subject_requests CASCADE;
DROP TABLE IF EXISTS legal.data_processing_authorizations CASCADE;
DROP TABLE IF EXISTS legal.ai_data_processing_profiles CASCADE;
DROP TABLE IF EXISTS legal.ai_provider_profiles CASCADE;
DROP TABLE IF EXISTS legal.ai_compliance_evidence CASCADE;
DROP TABLE IF EXISTS legal.ai_risk_assessments CASCADE;
DROP TABLE IF EXISTS legal.ai_system_capability_bindings CASCADE;
DROP TABLE IF EXISTS legal.workspace_ai_deployments CASCADE;
DROP TABLE IF EXISTS legal.ai_system_versions CASCADE;
DROP TABLE IF EXISTS legal.ai_system_catalog CASCADE;
DROP TABLE IF EXISTS legal.obligation_transitions CASCADE;
DROP TABLE IF EXISTS legal.legal_obligation_instances CASCADE;
DROP TABLE IF EXISTS legal.applicability_evaluations CASCADE;
DROP TABLE IF EXISTS legal.applicability_rules CASCADE;
DROP TABLE IF EXISTS legal.legal_obligation_templates CASCADE;
DROP TABLE IF EXISTS legal.legal_verification_approvals CASCADE;
DROP TABLE IF EXISTS legal.legal_entity_profiles CASCADE;
DROP TABLE IF EXISTS legal.regulation_versions CASCADE;
DROP TABLE IF EXISTS legal.regulation_sources CASCADE;
