DO $$
DECLARE t RECORD;
BEGIN
  FOR t IN SELECT * FROM (VALUES
    ('agent','run_events','sequence_no'),
    ('agent','runtime_signal_outbox','sequence'),
    ('agent_conversation','messages','sequence_no'),
    ('agent_conversation','run_stream_events','sequence')
  ) AS v(nsp,rel,col) LOOP
    EXECUTE format('ALTER TABLE %I.%I ALTER COLUMN %I DROP IDENTITY IF EXISTS', t.nsp, t.rel, t.col);
  END LOOP;
END $$;
