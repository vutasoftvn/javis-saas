-- Rollback 11_dedupe_strategy_company_workspace_id.up.sql
ALTER TABLE strategy.next_action_rankings ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE strategy.next_action_candidates ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE strategy.decision_records ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE strategy.gate_evaluations ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE strategy.discovery_signals ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE strategy.interviews ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE strategy.evidence ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE strategy.experiments ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE strategy.assumptions ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE strategy.stage_policies ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE strategy.stage_transitions ADD COLUMN IF NOT EXISTS company_id BIGINT;
