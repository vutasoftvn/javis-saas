-- Down Migration 016: workforce_schedules, outcome_analysis_bindings,
-- local_upload_tickets. Chỉ rollback khi schedule/binding còn rỗng
-- (upload ticket là dữ liệu tạm có hạn, không chặn rollback).

DO $$
BEGIN
  IF to_regclass('agent.workforce_schedules') IS NOT NULL
     AND EXISTS (SELECT 1 FROM agent.workforce_schedules LIMIT 1) THEN
    RAISE EXCEPTION 'Cannot rollback migration 016: workforce_schedules contains data.';
  END IF;
  IF to_regclass('agent.outcome_analysis_bindings') IS NOT NULL
     AND EXISTS (SELECT 1 FROM agent.outcome_analysis_bindings LIMIT 1) THEN
    RAISE EXCEPTION 'Cannot rollback migration 016: outcome_analysis_bindings contains data.';
  END IF;
END $$;

DROP TABLE IF EXISTS agent.local_upload_tickets;
DROP TABLE IF EXISTS agent.outcome_analysis_bindings;
DROP TABLE IF EXISTS agent.workforce_schedules;
