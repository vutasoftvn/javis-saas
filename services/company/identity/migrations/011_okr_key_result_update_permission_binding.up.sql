-- 011_okr_key_result_update_permission_binding.up.sql
--
-- `okr.key_result.update` là capability T2 GHI qua company (AGENT_CAP.OKR_KEY_RESULT_UPDATE —
-- sửa status/target_value/current_value/unit của Key Result), nên live authorization vẫn đòi
-- ticket (LiveAuthorizationAuthorizer: T2 có AGENT_CAP cần ticket) và company cần binding
-- capability -> permission để cấp ticket (cùng lý do 009/010).
-- Permission riêng `okr.key_result.update`: chỉ sửa Key Result nội bộ, không tạo/xoá, không gọi
-- ra ngoài ⇒ risk_class INTERNAL_WRITE.
-- Test parity: tests/apps/cosa/test_agent_capability_grants_parity.py. Expand-only, idempotent.

INSERT INTO core.permission_definitions (permission_key, domain, description)
VALUES ('okr.key_result.update', 'operations', 'Cập nhật Key Result (status/target/current/unit) do agent đề xuất, founder duyệt')
ON CONFLICT (permission_key) DO NOTHING;

INSERT INTO core.capability_permission_bindings (capability_id, permission_key, risk_class, version)
VALUES
  ('okr.key_result.update', 'okr.key_result.update', 'INTERNAL_WRITE', 1)
ON CONFLICT (capability_id) DO NOTHING;
