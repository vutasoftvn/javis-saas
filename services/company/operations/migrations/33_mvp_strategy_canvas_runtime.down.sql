-- Rollback Migration 33

DROP TABLE IF EXISTS operating.runtime_snoozes;
DROP TABLE IF EXISTS operating.runtime_source_signals;
DROP TABLE IF EXISTS strategy.canvas_revisions;
DROP TABLE IF EXISTS strategy.canvases;
