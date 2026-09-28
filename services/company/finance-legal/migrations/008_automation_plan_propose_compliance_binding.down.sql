-- Rollback for 008_automation_plan_propose_compliance_binding.up.sql: gỡ đúng binding migration
-- này tạo (capability mới, chưa từng có binding trước đó).
DELETE FROM legal.ai_system_capability_bindings
WHERE capability_id = 'automation.plan.propose'
  AND system_version_id IN (
    SELECT v.id FROM legal.ai_system_versions v
    JOIN legal.ai_system_catalog c ON c.id = v.system_catalog_id
    WHERE c.system_key = 'cosa.agents.operations'
  );
