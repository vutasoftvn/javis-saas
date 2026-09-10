-- Inverse of 005: re-attach the (incorrect, per 004) identity. Only for rollback symmetry.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'agent' AND c.relname = 'runtime_signal_outbox'
      AND a.attname = 'sequence' AND a.attidentity <> ''
  ) THEN
    EXECUTE 'ALTER TABLE agent.runtime_signal_outbox ALTER COLUMN sequence ADD GENERATED ALWAYS AS IDENTITY';
  END IF;
END $$;
