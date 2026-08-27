-- Migration 14: Enforce connector installation uniqueness (dedup guard)
--
-- **CRITICAL WARNING**: Migration 13 contains a row-deleting dedup block (lines 54-61 of 13_workspace_only_product_scope.up.sql).
-- That DELETE operation must NOT be applied to production databases without manual resolution.
--
-- Production deployment runbook (required before applying migrations 13+14):
-- 1. Run the duplicate-check query (see below) on the target database.
-- 2. Manually resolve any duplicates (keep the most recent, archive/delete others).
-- 3. THEN apply migrations 13 and 14.
--
-- This migration 14 enforces the invariant: after migration 13 is applied, there must be
-- no duplicate (workspace_id, connector_key) pairs in control_plane.workspace_connector_installations.
-- If duplicates exist, this migration fails hard (RAISE EXCEPTION) to flag the issue.

-- Check for duplicate (workspace_id, connector_key) pairs in workspace_connector_installations
-- If any exist, raise an exception to fail loudly (safe to re-run).
DO $$
DECLARE
  dup_count INT;
BEGIN
  -- Count pairs of (workspace_id, connector_key) that have more than one row
  SELECT COUNT(DISTINCT (workspace_id, connector_key))
  INTO dup_count
  FROM control_plane.workspace_connector_installations
  GROUP BY workspace_id, connector_key
  HAVING COUNT(*) > 1;

  IF dup_count > 0 THEN
    RAISE EXCEPTION 'MIGRATION_BLOCKED: workspace_connector_installations có % tổ hợp (workspace_id, connector_key) bị trùng lặp. Phải giải quyết thủ công trước khi áp dụng migration này.', dup_count;
  END IF;
END $$;

-- Query to identify duplicates (for manual resolution):
-- SELECT workspace_id, connector_key, COUNT(*) as count, array_agg(id ORDER BY created_at DESC) as ids
-- FROM control_plane.workspace_connector_installations
-- GROUP BY workspace_id, connector_key
-- HAVING COUNT(*) > 1
-- ORDER BY workspace_id, connector_key;
