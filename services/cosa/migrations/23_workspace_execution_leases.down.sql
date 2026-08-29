-- Revert M6 §2.
DROP TABLE IF EXISTS control_plane.workspace_execution_leases;
DROP SEQUENCE IF EXISTS control_plane.workspace_execution_fencing_seq;
