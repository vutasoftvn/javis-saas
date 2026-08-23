-- services/company/operations/migrations/11_dedupe_strategy_company_workspace_id.up.sql

-- Canonical tenant key trong Company DB = workspace_id duy nhất.
-- core.workspaces.platform_company_id là nơi duy nhất giữ mapping sang
-- COSA companyId — business row không lưu song song company_id +
-- workspace_id nữa. Xem Plan B, nguyên tắc canonical tenant key.
ALTER TABLE strategy.stage_policies DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.stage_transitions DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.assumptions DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.experiments DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.evidence DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.interviews DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.discovery_signals DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.gate_evaluations DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.decision_records DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.next_action_candidates DROP COLUMN IF EXISTS company_id;
ALTER TABLE strategy.next_action_rankings DROP COLUMN IF EXISTS company_id;
