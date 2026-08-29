-- Rollback 001_canonical_agent_schema.sql
DROP TABLE IF EXISTS agent.approvals CASCADE;
DROP TABLE IF EXISTS agent.run_events CASCADE;
DROP TABLE IF EXISTS agent.run_tool_calls CASCADE;
DROP TABLE IF EXISTS agent.run_state_transitions CASCADE;
DROP TABLE IF EXISTS agent.runs CASCADE;
DROP TABLE IF EXISTS agent.leases CASCADE;
