-- Down Migration 018: Founder-Configurable Role, Agent, Skill & Workflow Storage
-- Chỉ drop trong disposable database trống; abort nếu có dữ liệu.

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM operating.founder_asset_events LIMIT 1) OR
     EXISTS (SELECT 1 FROM operating.project_workflow_bindings LIMIT 1) OR
     EXISTS (SELECT 1 FROM operating.project_agent_deployments LIMIT 1) OR
     EXISTS (SELECT 1 FROM operating.project_role_deployments LIMIT 1) OR
     EXISTS (SELECT 1 FROM operating.role_agent_bindings LIMIT 1) OR
     EXISTS (SELECT 1 FROM operating.workspace_agents LIMIT 1) OR
     EXISTS (SELECT 1 FROM operating.workspace_operating_roles LIMIT 1) THEN
    RAISE EXCEPTION 'Cannot rollback migration 018: tables contain data.';
  END IF;
END $$;

DROP TABLE IF EXISTS operating.founder_asset_events;
DROP TABLE IF EXISTS operating.project_workflow_bindings;
DROP TABLE IF EXISTS operating.project_agent_deployments;
DROP TABLE IF EXISTS operating.project_role_deployments;
DROP TABLE IF EXISTS operating.role_agent_bindings;
DROP TABLE IF EXISTS operating.workspace_agents;
DROP TABLE IF EXISTS operating.workspace_operating_roles;
