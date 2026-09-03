-- Migration down: 025_workforce_schedules.down.sql
-- Description: Reversible rollback for workforce schedules.

DROP INDEX IF EXISTS agent.idx_workforce_schedules_ws_status;
DROP TABLE IF EXISTS agent.workforce_schedules;
