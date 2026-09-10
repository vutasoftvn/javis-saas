-- SP-A Task 5A: migration 004 wrongly attached GENERATED ALWAYS AS IDENTITY to
-- agent.runtime_signal_outbox.sequence. That column is a caller-supplied natural-key
-- component (enqueue_runtime_signal inserts it explicitly; pre-squash 022_* and the
-- current baseline 001 both declare it plain `sequence BIGINT NOT NULL`). Detach the
-- identity so explicit inserts work again. 004 is checksum-immutable — do NOT edit it.
-- Non-destructive: the column keeps its data, type (bigint) and NOT NULL; only the
-- auto-generation is removed. Idempotent.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'agent' AND c.relname = 'runtime_signal_outbox'
      AND a.attname = 'sequence' AND a.attidentity <> ''
  ) THEN
    EXECUTE 'ALTER TABLE agent.runtime_signal_outbox ALTER COLUMN sequence DROP IDENTITY IF EXISTS';
  END IF;
END $$;
