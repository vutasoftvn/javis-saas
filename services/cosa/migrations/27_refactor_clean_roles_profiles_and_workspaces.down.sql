-- services/cosa/migrations/27_refactor_clean_roles_profiles_and_workspaces.down.sql

ALTER TABLE cosa.profiles DROP COLUMN IF EXISTS headline;
ALTER TABLE cosa.profiles DROP COLUMN IF EXISTS bio;
ALTER TABLE cosa.profiles DROP COLUMN IF EXISTS role_id;

ALTER TABLE cosa.roles DROP COLUMN IF EXISTS sort_order;
ALTER TABLE cosa.roles DROP COLUMN IF EXISTS category;
ALTER TABLE cosa.roles DROP COLUMN IF EXISTS name;
