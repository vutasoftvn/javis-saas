-- Rollback 7_control_plane_leases_workers.up.sql
DROP TABLE IF EXISTS control_plane.scheduled_tasks CASCADE;
DROP TABLE IF EXISTS control_plane.runtime_leases CASCADE;
DROP TABLE IF EXISTS control_plane.workers CASCADE;
