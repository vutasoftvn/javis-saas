-- Migrate strategy module to snowflake IDs
-- Remove bigserial defaults from all strategy tables

TRUNCATE TABLE strategy.assumptions, strategy.decision_records, strategy.discovery_signals, strategy.evidence, strategy.experiments, strategy.gate_evaluations, strategy.interviews, strategy.next_action_candidates, strategy.next_action_rankings, strategy.stage_policies, strategy.stage_transitions CASCADE;

ALTER TABLE strategy.assumptions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.decision_records ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.discovery_signals ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.evidence ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.experiments ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.gate_evaluations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.interviews ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.next_action_candidates ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.next_action_rankings ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.stage_policies ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.stage_transitions ALTER COLUMN id DROP DEFAULT;
