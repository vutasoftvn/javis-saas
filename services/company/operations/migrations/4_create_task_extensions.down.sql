-- Rollback 4_create_task_extensions.up.sql
DROP TABLE IF EXISTS operating.task_dependencies CASCADE;
DROP TABLE IF EXISTS operating.task_schedules CASCADE;
