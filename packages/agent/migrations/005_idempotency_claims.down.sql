-- Rollback 005_idempotency_claims.sql
DROP TABLE IF EXISTS agent.idempotency_claims CASCADE;
