-- Rollback 17_local_event_outbox.up.sql
DROP TABLE IF EXISTS integration.event_outbox CASCADE;
