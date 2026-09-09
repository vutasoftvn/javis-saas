-- Rollback 003_cosa_automation_mvp.up.sql (child tables first).
DROP TABLE IF EXISTS operating.automation_invocation_events;
DROP TABLE IF EXISTS operating.automation_invocations;
DROP TABLE IF EXISTS operating.automation_revisions;
DROP TABLE IF EXISTS operating.automation_definitions;
