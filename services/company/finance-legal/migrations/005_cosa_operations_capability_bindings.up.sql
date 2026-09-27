-- 005_cosa_operations_capability_bindings.up.sql
--
-- Spec 2026-09-27-chat-business-actions / ADR-CHAT-ACTIONS-001: spec `cosa.agents.operations`
-- 1.6.0 xin thêm capability (business.read và các capability đọc nó dispatch tới, OKR, goal,
-- triage, task.advance, venture). Snapshot compliance runtime yêu cầu MỌI capability xin có
-- binding trên system version của deployment, thiếu 1 cái là 404 cho cả run. Bổ sung binding
-- cho mọi system version thuộc catalog `cosa.agents.operations` đang tồn tại. Hành động ghi
-- (DRAFT) luôn requires_human_confirmation = true (founder duyệt trong chat).
-- Danh sách PHẢI phủ đúng tập ComplianceResolver xin — test parity
-- tests/apps/cosa/test_agent_capability_grants_parity.py. Expand-only, idempotent.

WITH wanted(capability_id, effect_class, decision_domain, requires_human_confirmation, may_send_to_model) AS (
  VALUES
    ('operations.task.list', 'READ', 'OPERATIONS', false, false),
    ('operations.task.read', 'READ', 'OPERATIONS', false, false),
    ('operations.task.create_draft', 'DRAFT', 'OPERATIONS', true, false),
    ('strategy.project.get', 'READ', 'OPERATIONS', false, false),
    ('strategy.next_best_action.get', 'READ', 'OPERATIONS', false, false),
    ('strategy.evidence.list', 'READ', 'OPERATIONS', false, false),
    ('analytics.metric_contract.get', 'READ', 'OPERATIONS', false, false),
    ('knowledge.profile.read', 'READ', 'OPERATIONS', false, false),
    ('workspace.context.read', 'READ', 'OPERATIONS', false, false),
    ('operations.execution_plan.read', 'READ', 'OPERATIONS', false, false),
    ('business.read', 'READ', 'OPERATIONS', false, false),
    ('okr.objective.list', 'READ', 'OPERATIONS', false, false),
    ('okr.key_result.create', 'DRAFT', 'OPERATIONS', true, false),
    ('okr.key_result.checkin', 'DRAFT', 'OPERATIONS', true, false),
    ('startup_os.goal.create', 'DRAFT', 'OPERATIONS', true, false),
    ('startup_os.project.triage', 'DRAFT', 'OPERATIONS', true, false),
    ('operations.task.advance', 'DRAFT', 'OPERATIONS', true, false),
    ('venture.profile.propose_update', 'DRAFT', 'OPERATIONS', true, false),
    ('ai.governance.read', 'READ', 'OPERATIONS', false, false),
    ('commercial.marketing_context.read', 'READ', 'COMMERCIAL', false, false),
    ('data.governance.read', 'READ', 'OPERATIONS', false, false),
    ('finance.transaction.read', 'READ', 'FINANCE', false, false),
    ('legal.issue.read', 'READ', 'LEGAL', false, false),
    ('people.risk.read', 'READ', 'HR', false, false),
    ('product.decision.read', 'READ', 'OPERATIONS', false, false),
    ('project.crm.read', 'READ', 'COMMERCIAL', false, false),
    ('security.posture.read', 'READ', 'OPERATIONS', false, false),
    ('startup_os.goal.tree_read', 'READ', 'OPERATIONS', false, false),
    ('venture.profile.read', 'READ', 'OPERATIONS', false, false),
    ('model.input.direct-user-message', 'READ', 'OPERATIONS', false, true)
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
