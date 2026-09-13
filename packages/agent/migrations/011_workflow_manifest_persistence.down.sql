-- Down migration 011: Workflow Definition, Execution Manifest & Step Record Persistence

DROP TABLE IF EXISTS agent.workflow_step_records;
DROP TABLE IF EXISTS agent.workflow_execution_manifests;
DROP TABLE IF EXISTS agent.workflow_definitions;
