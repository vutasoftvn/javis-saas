-- services/company/operations/migrations/23_task_execution_records.down.sql
DROP INDEX IF EXISTS operating.idx_task_execution_records_ws_task;
DROP TABLE IF EXISTS operating.task_execution_records CASCADE;
