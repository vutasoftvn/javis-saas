ALTER TABLE core.workspaces
  ADD COLUMN IF NOT EXISTS platform_workspace_id TEXT UNIQUE,
  ADD COLUMN IF NOT EXISTS venture_stage_entered_at TIMESTAMPTZ;

