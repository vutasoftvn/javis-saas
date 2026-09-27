-- 031_backfill_founder_notify_send_grant.up.sql
--
-- ADR-FOUNDER-CHANNEL-001 / plan hub đợt 2 B2: spec `cosa.agents.operations` 1.7.0 thêm
-- `founder.notify.send` và bảng TS AGENT_PROFILE_GRANTED_CAPABILITIES
-- (operations/services/agent-profile-grants.service.ts) cấp nó cho AI member profile
-- `operations` khi founder kích hoạt Project team. Backfill cho assignment đã ACTIVE trước thay
-- đổi này — cùng cách làm với 030 (role `startup_team_agent` + permission + grant + event),
-- người cấp = founder đã kích hoạt (activated_by). Mỗi lần gửi vẫn cần founder duyệt trong chat
-- và live authorization ticket; grant chỉ là điều kiện cần.
-- Danh sách (profile, capability) PHẢI khớp bảng TS — test parity
-- tests/apps/cosa/test_agent_capability_grants_parity.py (hợp 030 + 031). Expand-only, idempotent.

WITH wanted(profile_key, capability_id) AS (
  VALUES
    ('operations', 'founder.notify.send')
),
targets AS (
  SELECT DISTINCT a.workspace_id, a.agent_workforce_member_id, b.permission_key
  FROM operating.project_agent_assignments a
  JOIN wanted w ON w.profile_key = a.profile_key
  JOIN core.capability_permission_bindings b ON b.capability_id = w.capability_id
  JOIN core.workforce_members agent
    ON agent.id = a.agent_workforce_member_id
   AND agent.workspace_id = a.workspace_id
   AND agent.member_type = 'AI_AGENT'
  WHERE a.state = 'ACTIVE'
)
INSERT INTO core.workspace_roles (workspace_id, role_key, name, is_system, allowed_member_types)
SELECT DISTINCT workspace_id, 'startup_team_agent', 'Startup team agent', true, ARRAY['AI_AGENT']
FROM targets
ON CONFLICT (workspace_id, role_key) DO NOTHING;

WITH wanted(profile_key, capability_id) AS (
  VALUES
    ('operations', 'founder.notify.send')
),
targets AS (
  SELECT DISTINCT a.workspace_id, a.agent_workforce_member_id, b.permission_key
  FROM operating.project_agent_assignments a
  JOIN wanted w ON w.profile_key = a.profile_key
  JOIN core.capability_permission_bindings b ON b.capability_id = w.capability_id
  JOIN core.workforce_members agent
    ON agent.id = a.agent_workforce_member_id
   AND agent.workspace_id = a.workspace_id
   AND agent.member_type = 'AI_AGENT'
  WHERE a.state = 'ACTIVE'
)
INSERT INTO core.role_permissions (role_id, permission_key, effect)
SELECT DISTINCT r.id, t.permission_key, 'ALLOW'
FROM targets t
JOIN core.workspace_roles r ON r.workspace_id = t.workspace_id AND r.role_key = 'startup_team_agent'
ON CONFLICT (role_id, permission_key) DO NOTHING;

WITH wanted(profile_key, capability_id) AS (
  VALUES
    ('operations', 'founder.notify.send')
),
targets AS (
  SELECT DISTINCT a.workspace_id, a.agent_workforce_member_id
  FROM operating.project_agent_assignments a
  JOIN wanted w ON w.profile_key = a.profile_key
  JOIN core.workforce_members agent
    ON agent.id = a.agent_workforce_member_id
   AND agent.workspace_id = a.workspace_id
   AND agent.member_type = 'AI_AGENT'
  WHERE a.state = 'ACTIVE'
)
INSERT INTO core.member_role_assignments (workspace_id, workforce_member_id, role_id)
SELECT t.workspace_id, t.agent_workforce_member_id, r.id
FROM targets t
JOIN core.workspace_roles r ON r.workspace_id = t.workspace_id AND r.role_key = 'startup_team_agent'
WHERE NOT EXISTS (
  SELECT 1 FROM core.member_role_assignments m
  WHERE m.workspace_id = t.workspace_id
    AND m.workforce_member_id = t.agent_workforce_member_id
    AND m.role_id = r.id
);

WITH wanted(profile_key, capability_id) AS (
  VALUES
    ('operations', 'founder.notify.send')
),
inserted AS (
  INSERT INTO core.agent_capability_grants (
    workspace_id, agent_workforce_member_id, capability_id, project_id,
    constraints, status, granted_by_founder_member_id
  )
  SELECT a.workspace_id, a.agent_workforce_member_id, w.capability_id, a.project_id,
         '{}'::jsonb, 'ACTIVE', a.activated_by
  FROM operating.project_agent_assignments a
  JOIN wanted w ON w.profile_key = a.profile_key
  JOIN core.capability_permission_bindings b ON b.capability_id = w.capability_id
  JOIN core.workforce_members agent
    ON agent.id = a.agent_workforce_member_id
   AND agent.workspace_id = a.workspace_id
   AND agent.member_type = 'AI_AGENT'
  JOIN core.workforce_members founder
    ON founder.id = a.activated_by
   AND founder.workspace_id = a.workspace_id
   AND founder.member_type = 'HUMAN'
  WHERE a.state = 'ACTIVE'
    AND NOT EXISTS (
      SELECT 1 FROM core.agent_capability_grants g
      WHERE g.workspace_id = a.workspace_id
        AND g.agent_workforce_member_id = a.agent_workforce_member_id
        AND g.capability_id = w.capability_id
        AND g.project_id = a.project_id
        AND g.status = 'ACTIVE'
    )
  RETURNING id, workspace_id, agent_workforce_member_id, capability_id, project_id,
            granted_by_founder_member_id
)
INSERT INTO core.authorization_events (
  workspace_id, event_type, actor_member_id, target_member_id, capability_id, grant_id,
  reason, details
)
SELECT workspace_id, 'AGENT_CAPABILITY_GRANTED', granted_by_founder_member_id,
       agent_workforce_member_id, capability_id, id,
       'Startup team activation backfill (031)',
       jsonb_build_object('projectId', project_id::text)
FROM inserted;
