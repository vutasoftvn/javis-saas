-- Rollback 6_control_plane_missions_tasks.up.sql
DROP TABLE IF EXISTS control_plane.assignments CASCADE;
DROP TABLE IF EXISTS control_plane.tasks CASCADE;
DROP TABLE IF EXISTS control_plane.missions CASCADE;
