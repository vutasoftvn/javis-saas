-- Rollback 008_agent_evals.sql
DROP TABLE IF EXISTS agent_evals.skill_mutations CASCADE;
DROP TABLE IF EXISTS agent_evals.skill_candidates CASCADE;
DROP TABLE IF EXISTS agent_evals.results CASCADE;
DROP TABLE IF EXISTS agent_evals.runs CASCADE;
DROP TABLE IF EXISTS agent_evals.cases CASCADE;
DROP TABLE IF EXISTS agent_evals.suites CASCADE;
