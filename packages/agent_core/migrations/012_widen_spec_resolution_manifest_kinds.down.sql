-- Rollback 012_widen_spec_resolution_manifest_kinds.sql
ALTER TABLE agent_core_governance.spec_resolution_manifest_entries
    DROP CONSTRAINT IF EXISTS spec_resolution_manifest_entries_spec_kind_check;

ALTER TABLE agent_core_governance.spec_resolution_manifest_entries
    ADD CONSTRAINT spec_resolution_manifest_entries_spec_kind_check
    CHECK (spec_kind IN ('agent', 'workflow'));
