-- Revert M4 §1 — lifecycle_stage -> company_stage, stage_entered_at -> venture_stage_entered_at.

ALTER TABLE core.workspaces DROP CONSTRAINT IF EXISTS workspaces_lifecycle_stage_chk;

UPDATE core.workspaces SET lifecycle_stage = CASE lifecycle_stage
  WHEN 'W0_IDEA'                THEN 'S0_GENESIS'
  WHEN 'W1_PROBLEM_VALIDATION'  THEN 'S1_PROBLEM_VALIDATION'
  WHEN 'W2_SOLUTION_VALIDATION' THEN 'S2_SOLUTION_VALIDATION'
  WHEN 'W3_MVP_BUILD'           THEN 'S3_MVP_BUILD'
  WHEN 'W4_PRODUCT_MARKET_FIT'  THEN 'S4_PRODUCT_MARKET_FIT'
  WHEN 'W5_SCALE'               THEN 'S5_SCALE'
  ELSE lifecycle_stage
END;

ALTER TABLE core.workspaces ALTER COLUMN lifecycle_stage SET DEFAULT 'S0_GENESIS';
ALTER TABLE core.workspaces RENAME COLUMN lifecycle_stage TO company_stage;
ALTER TABLE core.workspaces RENAME COLUMN stage_entered_at TO venture_stage_entered_at;
