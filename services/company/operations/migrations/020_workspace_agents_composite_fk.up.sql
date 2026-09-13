-- Migration 020: Enforce composite FK (workforce_member_id, workspace_id) on workspace_agents
-- Đảm bảo chặn liên-tenant ở tầng database foreign key.

ALTER TABLE operating.workspace_agents
  DROP CONSTRAINT IF EXISTS fk_workspace_agents_member,
  ADD CONSTRAINT fk_workspace_agents_member
    FOREIGN KEY (workforce_member_id, workspace_id)
    REFERENCES core.workforce_members(id, workspace_id)
    ON DELETE RESTRICT;
