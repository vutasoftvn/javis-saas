-- Rollback 020_event_trigger_rules.sql
ALTER TABLE event_inbox
  DROP COLUMN IF EXISTS aggregate_id,
  DROP COLUMN IF EXISTS aggregate_type;

DROP TABLE IF EXISTS event_trigger_rules CASCADE;
