-- Rollback 3_create_okr.up.sql
DROP TABLE IF EXISTS strategy.key_results CASCADE;
DROP TABLE IF EXISTS strategy.okr_objectives CASCADE;
DROP TABLE IF EXISTS strategy.okr_cycles CASCADE;
