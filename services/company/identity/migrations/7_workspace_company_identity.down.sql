-- services/company/identity/migrations/7_workspace_company_identity.down.sql
ALTER TABLE core.workspaces
  DROP COLUMN vision,
  DROP COLUMN mission,
  DROP COLUMN core_values;
