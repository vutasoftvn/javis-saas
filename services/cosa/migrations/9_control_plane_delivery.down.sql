-- Rollback 9_control_plane_delivery.up.sql
DROP TABLE IF EXISTS control_plane.cost_ledger CASCADE;
DROP TABLE IF EXISTS control_plane.delivery_attempts CASCADE;
DROP TABLE IF EXISTS control_plane.delivery_policies CASCADE;
