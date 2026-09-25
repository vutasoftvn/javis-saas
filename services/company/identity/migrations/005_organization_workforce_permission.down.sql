-- Rollback for 005_organization_workforce_permission.up.sql
DELETE FROM core.permission_definitions WHERE permission_key = 'organization.workforce.manage';
