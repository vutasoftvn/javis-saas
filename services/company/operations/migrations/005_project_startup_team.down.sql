-- Migration 005 down: Revert project startup team tables and type
DROP TABLE IF EXISTS operating.project_agent_assignment_events CASCADE;
DROP TABLE IF EXISTS operating.project_agent_assignments CASCADE;
DROP TYPE IF EXISTS operating.project_agent_assignment_state;
