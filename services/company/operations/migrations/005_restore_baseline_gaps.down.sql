-- SP-A Task 5C3 rollback — DROP 53 bảng do `005_restore_baseline_gaps.up.sql` tạo.
-- CASCADE để gỡ kèm FK/index; thứ tự ~ ngược phụ thuộc (CASCADE khiến thứ tự không
-- bắt buộc). KHÔNG `DROP SCHEMA`. 4 FK ngược chiều trên bảng `001`/`004` bị CASCADE
-- gỡ theo bảng cha.

DROP TABLE IF EXISTS strategy.workspace_stage_transitions CASCADE;
DROP TABLE IF EXISTS strategy.weekly_reviews CASCADE;
DROP TABLE IF EXISTS strategy.venture_profiles CASCADE;
DROP TABLE IF EXISTS strategy.tows_options CASCADE;
DROP TABLE IF EXISTS strategy.tows_option_evaluations CASCADE;
DROP TABLE IF EXISTS strategy.swot_items CASCADE;
DROP TABLE IF EXISTS strategy.strategic_objectives CASCADE;
DROP TABLE IF EXISTS strategy.stage_transition_policies CASCADE;
DROP TABLE IF EXISTS strategy.stage_policies CASCADE;
DROP TABLE IF EXISTS strategy.resource_capability_assessments CASCADE;
DROP TABLE IF EXISTS strategy.project_stage_transitions CASCADE;
DROP TABLE IF EXISTS strategy.project_stage_transition_policies CASCADE;
DROP TABLE IF EXISTS strategy.portfolios CASCADE;
DROP TABLE IF EXISTS strategy.portfolio_projects CASCADE;
DROP TABLE IF EXISTS strategy.pmf_scoreboard_runs CASCADE;
DROP TABLE IF EXISTS strategy.pilot_runs CASCADE;
DROP TABLE IF EXISTS strategy.pestel_signals CASCADE;
DROP TABLE IF EXISTS strategy.okr_objectives CASCADE;
DROP TABLE IF EXISTS strategy.okr_cycles CASCADE;
DROP TABLE IF EXISTS strategy.next_best_actions CASCADE;
DROP TABLE IF EXISTS strategy.next_action_rankings CASCADE;
DROP TABLE IF EXISTS strategy.next_action_candidates CASCADE;
DROP TABLE IF EXISTS strategy.metric_snapshots CASCADE;
DROP TABLE IF EXISTS strategy.metric_contracts CASCADE;
DROP TABLE IF EXISTS strategy.maturity_assessments CASCADE;
DROP TABLE IF EXISTS strategy.key_results CASCADE;
DROP TABLE IF EXISTS strategy.initiatives CASCADE;
DROP TABLE IF EXISTS strategy.initiative_key_results CASCADE;
DROP TABLE IF EXISTS strategy.gate_evaluations CASCADE;
DROP TABLE IF EXISTS strategy.discovery_signals CASCADE;
DROP TABLE IF EXISTS strategy.bsc_focus_scopes CASCADE;
DROP TABLE IF EXISTS operating.workspace_execution_settings CASCADE;
DROP TABLE IF EXISTS operating.workspace_capability_policy CASCADE;
DROP TABLE IF EXISTS operating.work_package_reviews CASCADE;
DROP TABLE IF EXISTS operating.work_package_priority_events CASCADE;
DROP TABLE IF EXISTS operating.work_package_events CASCADE;
DROP TABLE IF EXISTS operating.work_package_attempts CASCADE;
DROP TABLE IF EXISTS operating.task_work_packages CASCADE;
DROP TABLE IF EXISTS operating.task_schedules CASCADE;
DROP TABLE IF EXISTS operating.task_results CASCADE;
DROP TABLE IF EXISTS operating.task_outcome_reviews CASCADE;
DROP TABLE IF EXISTS operating.task_outcome_kr_links CASCADE;
DROP TABLE IF EXISTS operating.task_outcome_contracts CASCADE;
DROP TABLE IF EXISTS operating.task_execution_records CASCADE;
DROP TABLE IF EXISTS operating.task_dependencies CASCADE;
DROP TABLE IF EXISTS operating.outcome_assessments CASCADE;
DROP TABLE IF EXISTS operating.outcome_analysis_requests CASCADE;
DROP TABLE IF EXISTS operating.kr_observations CASCADE;
DROP TABLE IF EXISTS operating.kr_contribution_assessments CASCADE;
DROP TABLE IF EXISTS operating.execution_plans CASCADE;
DROP TABLE IF EXISTS operating.execution_plan_items CASCADE;
DROP TABLE IF EXISTS operating.cycle_key_results CASCADE;
DROP TABLE IF EXISTS operating.commitment_key_results CASCADE;
