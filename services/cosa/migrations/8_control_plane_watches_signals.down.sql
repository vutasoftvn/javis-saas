-- Rollback 8_control_plane_watches_signals.up.sql
DROP TABLE IF EXISTS control_plane.signal_observations CASCADE;
DROP TABLE IF EXISTS control_plane.trigger_policies CASCADE;
DROP TABLE IF EXISTS control_plane.watches CASCADE;
