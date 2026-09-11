-- Rollback for 002_restore_control_plane_dormant_tables.up.sql
DROP TABLE IF EXISTS control_plane.automation_dispatches;
DROP TABLE IF EXISTS control_plane.cost_ledger;
DROP TABLE IF EXISTS control_plane.delivery_attempts;
DROP TABLE IF EXISTS control_plane.delivery_policies;
DROP TABLE IF EXISTS control_plane.signal_observations;
DROP TABLE IF EXISTS control_plane.trigger_policies;
DROP TABLE IF EXISTS control_plane.watches;
DROP TABLE IF EXISTS control_plane.assignments;
DROP TABLE IF EXISTS control_plane.tasks;
DROP TABLE IF EXISTS control_plane.missions;
