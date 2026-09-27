-- 006_founder_notify_send_compliance_binding.up.sql
--
-- ADR-FOUNDER-CHANNEL-001 Decision 9 / plan hub đợt 2 B2: spec `cosa.agents.operations` 1.7.0
-- xin thêm `founder.notify.send`. Snapshot compliance runtime yêu cầu MỌI capability xin có
-- binding trên system version của deployment (thiếu 1 cái là 404 cho cả run — xem 005). Nội dung
-- gửi có thể chứa dữ liệu cá nhân (vd. tóm tắt email) nên max_data_category = 'PERSONAL';
-- effect_class = 'EXTERNAL' (dữ liệu rời hệ thống tới Telegram), luôn cần founder xác nhận.
-- action_recipient_scope ghi rõ đích duy nhất là kênh của chính founder (không có người nhận khác).
-- Test parity: tests/apps/cosa/test_agent_capability_grants_parity.py. Expand-only, idempotent.

WITH wanted(capability_id, effect_class, decision_domain, requires_human_confirmation, may_send_to_model) AS (
  VALUES
    ('founder.notify.send', 'EXTERNAL', 'OPERATIONS', true, false)
)
INSERT INTO legal.ai_system_capability_bindings (
  id, system_version_id, capability_id, effect_class, decision_domain,
  requires_human_confirmation, may_send_to_model, max_data_category, action_recipient_scope,
  prohibited_purpose
)
SELECT
  (((extract(epoch from clock_timestamp()) * 1000)::bigint - 1704067200000) << 23)
    + row_number() OVER (ORDER BY v.id, w.capability_id),
  v.id, w.capability_id, w.effect_class, w.decision_domain,
  w.requires_human_confirmation, w.may_send_to_model, 'PERSONAL', 'FOUNDER_SELF', false
FROM legal.ai_system_versions v
JOIN legal.ai_system_catalog c ON c.id = v.system_catalog_id
CROSS JOIN wanted w
WHERE c.system_key = 'cosa.agents.operations'
ON CONFLICT (system_version_id, capability_id) DO NOTHING;
