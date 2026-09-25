-- 005_organization_workforce_permission.up.sql
--
-- Spec 2026-09-25 §7: quyền tường minh cho việc xếp AI workforce vào sơ đồ
-- tổ chức (POST /operations/organizations/:id/ai-workforce). Founder/co-founder
-- có sẵn qua wildcard; key này cho phép gán cho vai trò khác qua permissions API.
-- Expand-only, idempotent.
INSERT INTO core.permission_definitions (permission_key, domain, description)
VALUES ('organization.workforce.manage', 'identity', 'Xếp AI workforce vào sơ đồ tổ chức')
ON CONFLICT (permission_key) DO NOTHING;
