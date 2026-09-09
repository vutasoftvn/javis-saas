-- Down migration 036.
DROP TABLE IF EXISTS agent.workforce_delegation_events;
DROP INDEX IF EXISTS agent.idx_workforce_delegations_lookup;
DROP TABLE IF EXISTS agent.workforce_delegations;
