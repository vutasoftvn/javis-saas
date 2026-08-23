-- services/company/identity/migrations/8_workforce_manager_same_workspace.up.sql

-- manager_member_id trước đây chỉ FK tới id toàn cục, không ràng buộc cùng
-- workspace hay chặn self-reference (DB_FINAL_CUTOVER.md §6.4).
ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_manager_not_self
  CHECK (manager_member_id IS NULL OR manager_member_id <> id);

-- Composite FK same-workspace: cần unique (id, workspace_id) làm target trước.
ALTER TABLE core.workforce_members ADD CONSTRAINT uq_workforce_members_id_workspace
  UNIQUE (id, workspace_id);

ALTER TABLE core.workforce_members DROP CONSTRAINT workforce_members_manager_member_id_fkey;

ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_manager_same_workspace_fkey
  FOREIGN KEY (manager_member_id, workspace_id)
  REFERENCES core.workforce_members(id, workspace_id)
  ON DELETE SET NULL;
