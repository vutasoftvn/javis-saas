-- 001_founder_trial_mvp_baseline is a pg_dump --schema-only squash. pg_dump
-- emits `GENERATED ALWAYS AS IDENTITY` as a separate ALTER statement, and the
-- squash filter dropped those — so several auto-sequence columns landed as bare
-- `bigint NOT NULL`. The Python repositories insert these rows WITHOUT the
-- column (INSERT ... RETURNING sequence_no / sequence), relying on the DB to
-- fill it. Without identity every such insert fails the NOT NULL constraint:
--
--   agent.run_events.sequence_no
--   agent.runtime_signal_outbox.sequence
--   agent_conversation.messages.sequence_no
--   agent_conversation.run_stream_events.sequence
--
-- Re-attach identity only where missing (attidentity = ''): safe on a fresh
-- baseline DB (no rows) and a no-op on a DB migrated the pre-squash way.

DO $$
DECLARE
  t RECORD;
BEGIN
  FOR t IN
    SELECT * FROM (VALUES
      ('agent',              'run_events',        'sequence_no'),
      ('agent',              'runtime_signal_outbox', 'sequence'),
      ('agent_conversation', 'messages',          'sequence_no'),
      ('agent_conversation', 'run_stream_events', 'sequence')
    ) AS v(nsp, rel, col)
  LOOP
    IF EXISTS (
      SELECT 1 FROM pg_attribute a
      JOIN pg_class c ON c.oid = a.attrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = t.nsp AND c.relname = t.rel
        AND a.attname = t.col AND a.attidentity = '' AND NOT a.atthasdef AND NOT a.attisdropped
    ) THEN
      EXECUTE format(
        'ALTER TABLE %I.%I ALTER COLUMN %I ADD GENERATED ALWAYS AS IDENTITY',
        t.nsp, t.rel, t.col
      );
    END IF;
  END LOOP;
END $$;
