-- Rollback for 006_founder_notify_send_compliance_binding.up.sql: gỡ đúng binding migration này
-- tạo (capability mới, chưa từng có binding trước đó).
DELETE FROM legal.ai_system_capability_bindings
WHERE capability_id = 'founder.notify.send' AND action_recipient_scope = 'FOUNDER_SELF';
