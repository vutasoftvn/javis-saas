-- Rollback 005_idempotency_claims.sql
DROP TABLE IF EXISTS agent_core.idempotency_claims CASCADE;
