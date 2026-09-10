-- Rollback for 002_restore_engagement_baseline.up.sql
-- The `engagement` schema is self-contained (no inbound FK from other schemas;
-- CRM links are workspace-scoped refs, not constraints), so a full drop is safe.
DROP SCHEMA IF EXISTS engagement CASCADE;
