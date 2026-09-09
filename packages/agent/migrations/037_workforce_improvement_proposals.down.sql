-- Down migration 037.
DROP TABLE IF EXISTS agent.workforce_improvement_events;
DROP INDEX IF EXISTS agent.idx_workforce_improvement_proposals_ws;
DROP TABLE IF EXISTS agent.workforce_improvement_proposals;
