-- 021_workforce_reporting_integrity.down.sql
ALTER TABLE agent.workforce_assignments DROP CONSTRAINT IF EXISTS fk_workforce_assignments_reports_to;
ALTER TABLE agent.workforce_assignments DROP CONSTRAINT IF EXISTS chk_workforce_assignments_no_self_report;
DROP INDEX IF EXISTS agent.idx_workforce_assignments_ws_reports_to;
DROP INDEX IF EXISTS agent.uix_workforce_assignments_id_workspace;
