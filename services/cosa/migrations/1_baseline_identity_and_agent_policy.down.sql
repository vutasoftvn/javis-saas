-- Rollback 1_baseline_identity_and_agent_policy.up.sql
DROP TABLE IF EXISTS cosa.company_agent_policy CASCADE;
DROP TABLE IF EXISTS cosa.company_entitlements CASCADE;
DROP TABLE IF EXISTS cosa.company_memberships CASCADE;
DROP TABLE IF EXISTS cosa.licenses CASCADE;
DROP TABLE IF EXISTS cosa.plans CASCADE;
DROP TABLE IF EXISTS cosa.profiles CASCADE;
DROP TABLE IF EXISTS cosa.companies CASCADE;
DROP TABLE IF EXISTS cosa.users CASCADE;
DROP TABLE IF EXISTS cosa.roles CASCADE;
