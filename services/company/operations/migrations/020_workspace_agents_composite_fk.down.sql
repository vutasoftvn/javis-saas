-- Down Migration 020: Rollback composite FK on workspace_agents

ALTER TABLE operating.workspace_agents
  DROP CONSTRAINT IF EXISTS fk_workspace_agents_member,
  ADD CONSTRAINT fk_workspace_agents_member
    FOREIGN KEY (workforce_member_id)
    REFERENCES core.workforce_members(id)
    ON DELETE RESTRICT;
