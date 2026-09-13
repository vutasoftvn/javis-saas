-- Down migration 011: Workflow Definition, Execution Manifest & Step Record Persistence
-- Abort if any table contains data; drop only when empty.

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM agent.workflow_step_records LIMIT 1) OR
     EXISTS (SELECT 1 FROM agent.workflow_execution_manifests LIMIT 1) OR
     EXISTS (SELECT 1 FROM agent.workflow_definitions LIMIT 1) THEN
    RAISE EXCEPTION 'Cannot rollback migration 011: tables contain audit or definition data.';
  END IF;
END $$;

DROP TABLE IF EXISTS agent.workflow_step_records;
DROP TABLE IF EXISTS agent.workflow_execution_manifests;
DROP TABLE IF EXISTS agent.workflow_definitions;

