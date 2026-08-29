-- Rollback 002_governance_temporal_model.sql
DROP TABLE IF EXISTS agent_governance.spend_ledger CASCADE;
DROP TABLE IF EXISTS agent_governance.action_evidence_ledger CASCADE;
DROP TABLE IF EXISTS agent_governance.spec_resolution_manifest_entries CASCADE;
DROP TABLE IF EXISTS agent_governance.spec_change_history CASCADE;
