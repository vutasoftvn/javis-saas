-- Migration 47 down: Drop strategy analysis artifacts

DROP TABLE IF EXISTS strategy.swot_items;
DROP TABLE IF EXISTS strategy.resource_capability_assessments;
DROP TABLE IF EXISTS strategy.pestel_signals;
