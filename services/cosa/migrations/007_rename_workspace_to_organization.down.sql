ALTER TABLE cosa.organization_invitations RENAME COLUMN organization_id TO workspace_id;
ALTER TABLE cosa.organization_invitations RENAME TO workspace_invitations;

ALTER TABLE cosa.organization_memberships RENAME COLUMN organization_id TO platform_workspace_id;
ALTER TABLE cosa.organization_memberships RENAME TO workspace_memberships;

ALTER TABLE cosa.organizations RENAME COLUMN organization_name TO workspace_name;
ALTER TABLE cosa.organizations RENAME TO workspaces;
