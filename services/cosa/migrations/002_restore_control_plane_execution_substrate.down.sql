-- Rollback 002_restore_control_plane_execution_substrate.up.sql
-- runtime_leases trước (FK → workers), rồi scheduled_tasks, rồi workers.
DROP TABLE IF EXISTS control_plane.runtime_leases;
DROP TABLE IF EXISTS control_plane.scheduled_tasks;
DROP TABLE IF EXISTS control_plane.workers;
