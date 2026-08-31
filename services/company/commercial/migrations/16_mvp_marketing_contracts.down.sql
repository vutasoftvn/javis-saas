-- Migration 16 Rollback
DROP TABLE IF EXISTS commercial.marketing_proposals;
DROP TABLE IF EXISTS commercial.marketing_decisions;
DROP TABLE IF EXISTS commercial.marketing_attributions;
DROP TABLE IF EXISTS commercial.marketing_metric_observations;
DROP TABLE IF EXISTS commercial.marketing_metric_definitions;
DROP TABLE IF EXISTS commercial.marketing_learnings;
DROP TABLE IF EXISTS commercial.marketing_experiments;
DROP TABLE IF EXISTS commercial.marketing_objectives;

ALTER TABLE commercial.marketing_campaigns ALTER COLUMN budget SET DEFAULT 0.0;
