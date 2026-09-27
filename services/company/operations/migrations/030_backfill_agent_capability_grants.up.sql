-- 030_backfill_agent_capability_grants.up.sql
--
-- Spec 2026-09-27-chat-business-actions / ADR-CHAT-ACTIONS-001: từ nay kích hoạt profile trong
-- Project startup team cấp cho AI member các capability ghi của profile
-- (operations/services/agent-profile-grants.service.ts::AGENT_PROFILE_GRANTED_CAPABILITIES).
-- Backfill cho assignment đã ACTIVE trước thay đổi này, người cấp = founder đã kích hoạt
-- (activated_by). Bỏ qua dòng không xác định được founder hoặc AI member.
-- Danh sách (profile, capability) PHẢI khớp bảng TS — test parity
-- tests/apps/cosa/test_agent_capability_grants_parity.py. Expand-only, idempotent.

WITH wanted(profile_key, capability_id) AS (
  VALUES
    ('operations', 'operations.task.create_draft'),
    ('operations', 'operations.task.advance'),
    ('operations', 'okr.key_result.create'),
    ('operations', 'okr.key_result.checkin'),
    ('operations', 'startup_os.goal.create'),
    ('operations', 'startup_os.project.triage'),
    ('operations', 'venture.profile.propose_update'),
    ('finance', 'finance.transaction.classify_propose'),
    ('finance', 'finance.accounting_document.create_draft')
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
       'Startup team activation backfill (030)',
       jsonb_build_object('projectId', project_id::text)
FROM inserted;
