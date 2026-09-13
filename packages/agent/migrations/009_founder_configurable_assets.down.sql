-- Down Migration 009: Founder-Configurable Assets Storage
-- Abort if any table contains data; drop only new tables.

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM agent.asset_events LIMIT 1) OR
     EXISTS (SELECT 1 FROM agent.asset_evaluations LIMIT 1) OR
     EXISTS (SELECT 1 FROM agent.workspace_asset_versions LIMIT 1) OR
     EXISTS (SELECT 1 FROM agent.workspace_assets LIMIT 1) THEN
    RAISE EXCEPTION 'Cannot rollback migration 009: tables contain data.';
  END IF;
END $$;

DROP TABLE IF EXISTS agent.asset_events;
DROP TABLE IF EXISTS agent.asset_evaluations;
DROP TABLE IF EXISTS agent.workspace_asset_versions;
DROP TABLE IF EXISTS agent.workspace_assets;
