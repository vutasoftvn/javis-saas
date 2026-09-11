-- Down migration 005: Project Activity projection
--
-- Refuses to run if any activity event has ever been recorded — dropping
-- these tables would silently delete durable Project Activity audit
-- history that the (future) Activity Feed API depends on as its source of
-- truth. Only safe when the projection has never been written to.

DO $$
DECLARE
    activity_events bigint;
BEGIN
    SELECT count(*) INTO activity_events FROM agent.project_activity_events;

    IF activity_events > 0 THEN
        RAISE EXCEPTION
            'migration 005 down refused: % project_activity_events row(s) present — '
            'rolling back would silently delete durable Project Activity audit history',
            activity_events;
    END IF;
END $$;

DROP INDEX IF EXISTS agent.idx_project_activity_events_project;
DROP TABLE IF EXISTS agent.project_activity_events;
DROP TABLE IF EXISTS agent.project_activity_sequences;
DROP TABLE IF EXISTS agent.project_activity_idempotency;
