-- Rollback 004_restore_baseline_gaps.up.sql — bảng con trước bảng cha.
DROP TABLE IF EXISTS strategy.okr_objective_projects CASCADE;
DROP TABLE IF EXISTS operating.task_projects CASCADE;
DROP TABLE IF EXISTS operating.runtime_snoozes CASCADE;
DROP TABLE IF EXISTS operating.runtime_source_signals CASCADE;
DROP TABLE IF EXISTS strategy.canvas_revisions CASCADE;
DROP TABLE IF EXISTS strategy.canvases CASCADE;
