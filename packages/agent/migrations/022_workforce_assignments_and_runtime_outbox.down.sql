-- Migration down: 022_workforce_assignments_and_runtime_outbox.down.sql
-- Description: Reversible rollback for workforce assignments, runtime signal outbox, and run cost observations.

DROP INDEX IF EXISTS agent.idx_run_cost_observations_ws_time;
DROP INDEX IF EXISTS agent.idx_runtime_signal_outbox_pending;
DROP INDEX IF EXISTS agent.idx_workforce_assignments_reports_to;
DROP INDEX IF EXISTS agent.idx_workforce_assignments_ws_status;

DROP TABLE IF EXISTS agent.run_cost_observations;
DROP TABLE IF EXISTS agent.runtime_signal_outbox;
DROP TABLE IF EXISTS agent.workforce_assignments;
