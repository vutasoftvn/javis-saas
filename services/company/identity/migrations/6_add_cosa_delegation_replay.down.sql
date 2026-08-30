-- services/company/identity/migrations/6_add_cosa_delegation_replay.down.sql
DROP INDEX IF EXISTS core.cosa_delegation_replays_workspace_run_idx;
DROP TABLE IF EXISTS core.cosa_delegation_replays;
