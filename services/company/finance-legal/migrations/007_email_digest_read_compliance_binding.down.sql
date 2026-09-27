-- Rollback for 007_email_digest_read_compliance_binding.up.sql: gỡ đúng binding migration này
-- tạo (capability mới, chưa từng có binding trước đó), chỉ trên catalog cosa.agents.operations.
DELETE FROM legal.ai_system_capability_bindings b
USING legal.ai_system_versions v, legal.ai_system_catalog c
WHERE b.system_version_id = v.id
  AND c.id = v.system_catalog_id
  AND c.system_key = 'cosa.agents.operations'
  AND b.capability_id = 'email.digest.read';
