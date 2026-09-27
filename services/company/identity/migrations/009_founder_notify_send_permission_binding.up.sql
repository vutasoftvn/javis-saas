-- 009_founder_notify_send_permission_binding.up.sql
--
-- ADR-FOUNDER-CHANNEL-001 Decision 7 / plan hub đợt 2 B2: `founder.notify.send` là capability
-- T2 ghi qua company (AGENT_CAP.FOUNDER_NOTIFY_SEND), nên cũng phải có binding
-- capability -> permission để company cấp được live authorization ticket (cùng lý do migration
-- 007). Permission riêng `founder.notify.send` (không mượn permission ghi dữ liệu nội bộ):
-- dữ liệu rời hệ thống ra kênh ngoài của CHÍNH founder, risk_class EXTERNAL_WRITE.
-- Test parity: tests/apps/cosa/test_agent_capability_grants_parity.py.
-- Expand-only, idempotent.

INSERT INTO core.permission_definitions (permission_key, domain, description)
VALUES ('founder.notify.send', 'identity', 'Gửi thông báo vào kênh nhận đã xác minh của chính founder')
ON CONFLICT (permission_key) DO NOTHING;

INSERT INTO core.capability_permission_bindings (capability_id, permission_key, risk_class, version)
VALUES
  ('founder.notify.send', 'founder.notify.send', 'EXTERNAL_WRITE', 1)
ON CONFLICT (capability_id) DO NOTHING;
