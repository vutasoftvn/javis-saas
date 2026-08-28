-- Rollback 7_create_strategy_domain.up.sql
DROP TABLE IF EXISTS strategy.next_action_rankings CASCADE;
DROP TABLE IF EXISTS strategy.next_action_candidates CASCADE;
DROP TABLE IF EXISTS strategy.decision_records CASCADE;
DROP TABLE IF EXISTS strategy.gate_evaluations CASCADE;
DROP TABLE IF EXISTS strategy.discovery_signals CASCADE;
DROP TABLE IF EXISTS strategy.interviews CASCADE;
DROP TABLE IF EXISTS strategy.evidence CASCADE;
DROP TABLE IF EXISTS strategy.experiments CASCADE;
DROP TABLE IF EXISTS strategy.assumptions CASCADE;
DROP TABLE IF EXISTS strategy.stage_policies CASCADE;
DROP TABLE IF EXISTS strategy.stage_transitions CASCADE;
