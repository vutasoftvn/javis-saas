-- Migration 38 down: revert entity-aware snapshot uniqueness

DROP INDEX IF EXISTS finance.financial_snapshots_workspace_snapshot_currency_entity_key;

ALTER TABLE finance.financial_snapshots
  ADD CONSTRAINT financial_snapshots_workspace_snapshot_currency_key
  UNIQUE (workspace_id, snapshot_date, currency);
