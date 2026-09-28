-- Rollback for 035_backfill_okr_key_result_update_grant.up.sql: chỉ gỡ grant do chính backfill này
-- tạo. Không xoá role `startup_team_agent` hay role_permissions (có thể do 030/031/033/kích hoạt tạo).
DELETE FROM core.agent_capability_grants
WHERE id IN (
  SELECT grant_id FROM core.authorization_events
  WHERE reason = 'Startup team activation backfill (035)' AND grant_id IS NOT NULL
);
DELETE FROM core.authorization_events WHERE reason = 'Startup team activation backfill (035)';
