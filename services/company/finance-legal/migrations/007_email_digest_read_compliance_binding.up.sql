-- 007_email_digest_read_compliance_binding.up.sql
--
-- Plan hub vận hành đợt 2 B3: spec `cosa.agents.operations` 1.8.0 xin thêm `email.digest.read`
-- (T0 — đọc tiêu đề/người gửi/đoạn trích email chưa đọc của founder qua grant connector
-- `email-read`, scope `mail:read`). Snapshot compliance runtime yêu cầu MỌI capability xin có
-- binding trên system version của deployment (thiếu 1 cái là 404 "out of scope" cho cả run —
-- xem 005). Email chứa dữ liệu cá nhân ⇒ max_data_category = 'PERSONAL'. Tóm tắt phải đưa vào
-- model để soạn digest ⇒ may_send_to_model = true. Chỉ đọc ⇒ READ, không cần founder xác nhận.
-- Test parity: tests/apps/cosa/test_agent_capability_grants_parity.py. Expand-only, idempotent.

WITH wanted(capability_id, effect_class, decision_domain, requires_human_confirmation, may_send_to_model) AS (
  VALUES
    ('email.digest.read', 'READ', 'OPERATIONS', false, true)
)
INSERT INTO legal.ai_system_capability_bindings (
  id, system_version_id, capability_id, effect_class, decision_domain,
  requires_human_confirmation, may_send_to_model, max_data_category, prohibited_purpose
)
SELECT
  (((extract(epoch from clock_timestamp()) * 1000)::bigint - 1704067200000) << 23)
    + row_number() OVER (ORDER BY v.id, w.capability_id),
  v.id, w.capability_id, w.effect_class, w.decision_domain,
  w.requires_human_confirmation, w.may_send_to_model, 'PERSONAL', false
FROM legal.ai_system_versions v
JOIN legal.ai_system_catalog c ON c.id = v.system_catalog_id
CROSS JOIN wanted w
WHERE c.system_key = 'cosa.agents.operations'
ON CONFLICT (system_version_id, capability_id) DO NOTHING;
