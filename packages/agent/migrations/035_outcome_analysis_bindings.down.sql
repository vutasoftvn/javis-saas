-- Down migration 035.
DROP INDEX IF EXISTS agent.idx_outcome_analysis_bindings_employee;
DROP TABLE IF EXISTS agent.outcome_analysis_bindings;
