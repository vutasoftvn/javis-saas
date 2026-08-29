DROP INDEX IF EXISTS core.uq_workspaces_platform_workspace_id;
ALTER TABLE core.workspaces DROP COLUMN IF EXISTS platform_workspace_id;
ALTER TABLE core.workspaces DROP COLUMN IF EXISTS venture_stage_entered_at;
