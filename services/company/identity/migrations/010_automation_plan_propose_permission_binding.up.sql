-- 010_automation_plan_propose_permission_binding.up.sql
--
-- Plan hub vận hành đợt 2 B4: `automation.plan.propose` là capability T1 (nháp) GHI qua company
-- (AGENT_CAP.AUTOMATION_PLAN_PROPOSE — lưu nháp vào operating.automation_plan_proposals), nên
-- live authorization vẫn đòi ticket (LiveAuthorizationAuthorizer: T1 có AGENT_CAP cần ticket) và
-- company cần binding capability -> permission để cấp ticket (cùng lý do 007/009).
-- Permission riêng `automation.plan.propose`: chỉ tạo nháp kế hoạch, không tạo lịch thật,
-- không gọi ra ngoài ⇒ risk_class INTERNAL_WRITE.
-- Test parity: tests/apps/cosa/test_agent_capability_grants_parity.py. Expand-only, idempotent.

INSERT INTO core.permission_definitions (permission_key, domain, description)
VALUES ('automation.plan.propose', 'operations', 'Đề xuất nháp kế hoạch tự động hoá cho founder duyệt')
ON CONFLICT (permission_key) DO NOTHING;

INSERT INTO core.capability_permission_bindings (capability_id, permission_key, risk_class, version)
VALUES
  ('automation.plan.propose', 'automation.plan.propose', 'INTERNAL_WRITE', 1)
ON CONFLICT (capability_id) DO NOTHING;
