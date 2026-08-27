-- Migration 13: Drop company_id từ 5 product-scope control_plane tables
-- (workspace_connector_installations, connector_authorizations, session_connector_grants,
-- workspace_schedule_definitions, workspace_schedule_executions) — Workspace-only product scope.
--
-- Lý do: Product scope (connector/schedule/policy) thuộc workspace, không phải company.
-- Tất cả 5 bảng đã có workspace_id, không còn cần company_id dự phòng.
-- Control-plane tables khác (missions, tasks, workers, leases, watches, etc.) không bị
-- ảnh hưởng; companyAgentPolicy ở cosa schema vẫn giữ company_id (private platform layer).

-- Safety check: Đảm bảo không có row nào có workspace_id IS NULL trước khi drop.
DO $$
DECLARE
  null_count INT;
BEGIN
  SELECT COUNT(*) INTO null_count
  FROM control_plane.workspace_connector_installations
  WHERE workspace_id IS NULL;
  IF null_count > 0 THEN
    RAISE EXCEPTION 'MIGRATION_BLOCKED: workspace_connector_installations có % rows với workspace_id IS NULL', null_count;
  END IF;

  SELECT COUNT(*) INTO null_count
  FROM control_plane.connector_authorizations
  WHERE workspace_id IS NULL;
  IF null_count > 0 THEN
    RAISE EXCEPTION 'MIGRATION_BLOCKED: connector_authorizations có % rows với workspace_id IS NULL', null_count;
  END IF;

  SELECT COUNT(*) INTO null_count
  FROM control_plane.session_connector_grants
  WHERE workspace_id IS NULL;
  IF null_count > 0 THEN
    RAISE EXCEPTION 'MIGRATION_BLOCKED: session_connector_grants có % rows với workspace_id IS NULL', null_count;
  END IF;

  SELECT COUNT(*) INTO null_count
  FROM control_plane.workspace_schedule_definitions
  WHERE workspace_id IS NULL;
  IF null_count > 0 THEN
    RAISE EXCEPTION 'MIGRATION_BLOCKED: workspace_schedule_definitions có % rows với workspace_id IS NULL', null_count;
  END IF;

  SELECT COUNT(*) INTO null_count
  FROM control_plane.workspace_schedule_executions
  WHERE workspace_id IS NULL;
  IF null_count > 0 THEN
    RAISE EXCEPTION 'MIGRATION_BLOCKED: workspace_schedule_executions có % rows với workspace_id IS NULL', null_count;
  END IF;
END $$;

-- Drop company_id từ workspace_connector_installations + update unique constraint
-- First, check for duplicate (workspace_id, connector_key) pairs that differ only by company_id.
-- If found, keep only the most recent one per (workspace_id, connector_key), delete others.
DELETE FROM control_plane.workspace_connector_installations wci1
WHERE EXISTS (
  SELECT 1
  FROM control_plane.workspace_connector_installations wci2
  WHERE wci1.workspace_id = wci2.workspace_id
    AND wci1.connector_key = wci2.connector_key
    AND wci1.id < wci2.id  -- Keep the newer one (higher id)
);

-- Now safe to drop the old constraint and column
ALTER TABLE control_plane.workspace_connector_installations
  DROP CONSTRAINT uq_connector_installation;

ALTER TABLE control_plane.workspace_connector_installations
  DROP COLUMN company_id;

-- Create new constraint on workspace_id + connector_key only
ALTER TABLE control_plane.workspace_connector_installations
  ADD CONSTRAINT uq_connector_installation UNIQUE (workspace_id, connector_key);

-- Drop company_id từ connector_authorizations + drop index
DROP INDEX IF EXISTS control_plane.idx_connector_authorizations_tenant;

ALTER TABLE control_plane.connector_authorizations
  DROP COLUMN company_id;

CREATE INDEX idx_connector_authorizations_workspace
  ON control_plane.connector_authorizations(workspace_id);

-- Drop company_id từ session_connector_grants
ALTER TABLE control_plane.session_connector_grants
  DROP COLUMN company_id;

-- Drop company_id từ workspace_schedule_definitions
ALTER TABLE control_plane.workspace_schedule_definitions
  DROP COLUMN company_id;

-- Drop company_id từ workspace_schedule_executions
ALTER TABLE control_plane.workspace_schedule_executions
  DROP COLUMN company_id;
