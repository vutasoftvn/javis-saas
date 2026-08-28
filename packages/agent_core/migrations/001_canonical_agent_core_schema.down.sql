-- Rollback 001_canonical_agent_core_schema.sql
DROP TABLE IF EXISTS agent_core.approvals CASCADE;
DROP TABLE IF EXISTS agent_core.run_events CASCADE;
DROP TABLE IF EXISTS agent_core.run_tool_calls CASCADE;
DROP TABLE IF EXISTS agent_core.run_state_transitions CASCADE;
DROP TABLE IF EXISTS agent_core.runs CASCADE;
DROP TABLE IF EXISTS agent_core.leases CASCADE;
