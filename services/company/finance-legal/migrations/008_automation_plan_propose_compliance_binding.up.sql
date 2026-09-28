-- 008_automation_plan_propose_compliance_binding.up.sql
--
-- Plan hub vận hành đợt 2 B4: spec `cosa.agents.operations` 1.9.0 xin thêm
-- `automation.plan.propose`. Snapshot compliance runtime yêu cầu MỌI capability xin có binding
-- trên system version của deployment (thiếu 1 cái là 404 cho cả run — xem 005). Capability chỉ
-- lưu NHÁP kế hoạch (effect_class 'DRAFT'); kế hoạch chỉ chạy sau khi founder duyệt thẻ kế hoạch
-- ⇒ requires_human_confirmation = true; may_send_to_model = false (cùng mẫu DRAFT của 005).
-- Test parity: tests/apps/cosa/test_agent_capability_grants_parity.py. Expand-only, idempotent.

WITH wanted(capability_id, effect_class, decision_domain, requires_human_confirmation, may_send_to_model) AS (
  VALUES
    ('automation.plan.propose', 'DRAFT', 'OPERATIONS', true, false)
)
INSERT INTO legal.ai_system_capability_bindings (
  id, system_version_id, capability_id, effect_class, decision_domain,
  requires_human_confirmation, may_send_to_model, max_data_category, prohibited_purpose
)
SELECT
  (((extract(epoch from clock_timestamp()) * 1000)::bigint - 1704067200000) << 23)
    + row_number() OVER (ORDER BY v.id, w.capability_id),
  v.id, w.capability_id, w.effect_class, w.decision_domain,
  w.requires_human_confirmation, w.may_send_to_model, 'BUSINESS_CONFIDENTIAL', false
FROM legal.ai_system_versions v
JOIN legal.ai_system_catalog c ON c.id = v.system_catalog_id
CROSS JOIN wanted w
WHERE c.system_key = 'cosa.agents.operations'
ON CONFLICT (system_version_id, capability_id) DO NOTHING;
