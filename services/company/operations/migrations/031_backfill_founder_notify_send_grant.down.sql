-- Rollback for 031_backfill_founder_notify_send_grant.up.sql: chỉ gỡ grant do chính backfill này
-- tạo. Không xoá role `startup_team_agent` hay role_permissions (có thể do 030/kích hoạt tạo).
DELETE FROM core.agent_capability_grants
WHERE id IN (
  SELECT grant_id FROM core.authorization_events
  WHERE reason = 'Startup team activation backfill (031)' AND grant_id IS NOT NULL
);
DELETE FROM core.authorization_events WHERE reason = 'Startup team activation backfill (031)';
