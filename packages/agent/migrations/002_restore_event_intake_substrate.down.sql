-- Rollback 002_restore_event_intake_substrate.sql
DROP TABLE IF EXISTS public.event_trigger_rules;
DROP TABLE IF EXISTS public.event_inbox;
