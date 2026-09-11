-- Rollback for 004_restore_fencing_and_execution_leases.up.sql
DROP TABLE IF EXISTS control_plane.workspace_execution_leases;
DROP SEQUENCE IF EXISTS control_plane.workspace_execution_fencing_seq;
DROP SEQUENCE IF EXISTS control_plane.snowflake_fencing_seq;
