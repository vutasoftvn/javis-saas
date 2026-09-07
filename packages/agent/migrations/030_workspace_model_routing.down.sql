-- Migration 030 Rollback
DROP POLICY IF EXISTS workspace_model_policies_workspace_isolation ON models.workspace_model_policies;
DROP POLICY IF EXISTS model_provider_profiles_workspace_isolation ON models.model_provider_profiles;

DROP TABLE IF EXISTS models.workspace_model_policies;
DROP TABLE IF EXISTS models.model_provider_profiles;
