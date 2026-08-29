-- services/company/identity/migrations/5_workspace_lifecycle_stage.up.sql
-- M4 §1 — Workspace lifecycle stage tách hẳn khỏi "company stage".
--   company_stage            -> lifecycle_stage  (enum W0_IDEA..W5_SCALE)
--   venture_stage_entered_at -> stage_entered_at
-- stage_version đã có từ migration 3 (dùng cho CAS ở M4 §2).
-- Backfill S->W theo LEGACY_WORKSPACE_STAGE_TO_CANONICAL (M0 contract).

ALTER TABLE core.workspaces RENAME COLUMN company_stage TO lifecycle_stage;
ALTER TABLE core.workspaces RENAME COLUMN venture_stage_entered_at TO stage_entered_at;

UPDATE core.workspaces SET lifecycle_stage = CASE lifecycle_stage
  WHEN 'S0_GENESIS'             THEN 'W0_IDEA'
  WHEN 'S1_PROBLEM_VALIDATION'  THEN 'W1_PROBLEM_VALIDATION'
  WHEN 'S2_SOLUTION_VALIDATION' THEN 'W2_SOLUTION_VALIDATION'
  WHEN 'S3_MVP_BUILD'           THEN 'W3_MVP_BUILD'
  WHEN 'S4_PRODUCT_MARKET_FIT'  THEN 'W4_PRODUCT_MARKET_FIT'
  WHEN 'S5_SCALE'               THEN 'W5_SCALE'
  ELSE lifecycle_stage
END;

ALTER TABLE core.workspaces ALTER COLUMN lifecycle_stage SET DEFAULT 'W0_IDEA';

ALTER TABLE core.workspaces
  ADD CONSTRAINT workspaces_lifecycle_stage_chk
  CHECK (lifecycle_stage IN (
    'W0_IDEA','W1_PROBLEM_VALIDATION','W2_SOLUTION_VALIDATION',
    'W3_MVP_BUILD','W4_PRODUCT_MARKET_FIT','W5_SCALE'
  ));
