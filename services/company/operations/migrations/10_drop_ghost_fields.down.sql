-- Rollback 10_drop_ghost_fields.up.sql
ALTER TABLE operating.tasks ADD COLUMN IF NOT EXISTS parent_task_id BIGINT;
ALTER TABLE operating.tasks ADD COLUMN IF NOT EXISTS description TEXT;
