-- 040_execution_plan_item_done_criteria.down.sql
ALTER TABLE operating.execution_plan_items
  DROP COLUMN IF EXISTS done_criteria;
