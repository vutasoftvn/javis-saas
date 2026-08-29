-- Migration: 012_widen_spec_resolution_manifest_kinds.sql
-- Description: Mở rộng CHECK constraint trên spec_kind của
--   agent_governance.spec_resolution_manifest_entries để khớp với
--   PinnedSpecIdentity.spec_kind đã mở rộng (ADR-ARTIFACT-IDENTITY-001) —
--   thêm 'skill', 'prompt', 'model_policy', 'tool_contract'.
-- Storage ownership: schema agent_governance owned by packages/agent/governance/.
--
-- 002_governance_temporal_model.sql đã apply là bất biến — không sửa file đó,
-- ALTER constraint bằng migration mới này thay vào đó.

ALTER TABLE agent_governance.spec_resolution_manifest_entries
    DROP CONSTRAINT IF EXISTS spec_resolution_manifest_entries_spec_kind_check;

ALTER TABLE agent_governance.spec_resolution_manifest_entries
    ADD CONSTRAINT spec_resolution_manifest_entries_spec_kind_check
    CHECK (spec_kind IN ('agent', 'workflow', 'skill', 'prompt', 'model_policy', 'tool_contract'));
