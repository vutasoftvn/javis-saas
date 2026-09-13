-- Down Migration 012: durable founder-asset callback outbox.
-- Never delete callback evidence that has not been reconciled.

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM agent.founder_asset_callback_outbox LIMIT 1) THEN
    RAISE EXCEPTION 'Cannot rollback migration 012: callback outbox contains data.';
  END IF;
END $$;

DROP TABLE IF EXISTS agent.founder_asset_callback_outbox;
