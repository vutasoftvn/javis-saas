-- services/company/operations/migrations/24_workspace_stage_lifecycle_rename.up.sql
-- M4 §1 — tách tên config policy khỏi history journal:
--   strategy.stage_transitions        -> strategy.stage_transition_policies   (config edge/policy)
--   strategy.venture_stage_transitions -> strategy.workspace_stage_transitions (history journal)
-- Backfill giá trị stage S->W trong journal (from_stage/to_stage) để đồng bộ với core.workspaces.
-- migration-compat: allow-destructive Canonical development reset is approved; no legacy data is retained.

ALTER TABLE strategy.stage_transitions RENAME TO stage_transition_policies;
ALTER TABLE strategy.venture_stage_transitions RENAME TO workspace_stage_transitions;

UPDATE strategy.workspace_stage_transitions SET
  from_stage = COALESCE(NULLIF(CASE from_stage
    WHEN 'S0_GENESIS' THEN 'W0_IDEA'
    WHEN 'S1_PROBLEM_VALIDATION' THEN 'W1_PROBLEM_VALIDATION'
    WHEN 'S2_SOLUTION_VALIDATION' THEN 'W2_SOLUTION_VALIDATION'
    WHEN 'S3_MVP_BUILD' THEN 'W3_MVP_BUILD'
    WHEN 'S4_PRODUCT_MARKET_FIT' THEN 'W4_PRODUCT_MARKET_FIT'
    WHEN 'S5_SCALE' THEN 'W5_SCALE'
    ELSE from_stage END, ''), from_stage),
  to_stage = COALESCE(NULLIF(CASE to_stage
    WHEN 'S0_GENESIS' THEN 'W0_IDEA'
    WHEN 'S1_PROBLEM_VALIDATION' THEN 'W1_PROBLEM_VALIDATION'
    WHEN 'S2_SOLUTION_VALIDATION' THEN 'W2_SOLUTION_VALIDATION'
    WHEN 'S3_MVP_BUILD' THEN 'W3_MVP_BUILD'
    WHEN 'S4_PRODUCT_MARKET_FIT' THEN 'W4_PRODUCT_MARKET_FIT'
    WHEN 'S5_SCALE' THEN 'W5_SCALE'
    ELSE to_stage END, ''), to_stage);
