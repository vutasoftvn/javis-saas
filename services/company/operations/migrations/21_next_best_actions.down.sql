-- services/company/operations/migrations/21_next_best_actions.down.sql
DROP INDEX IF EXISTS strategy.idx_next_best_actions_ws_status_priority;
DROP TABLE IF EXISTS strategy.next_best_actions CASCADE;
