-- Migrate operations module (13 tables) from bigserial to Snowflake IDs
-- Truncate all tables to clear existing auto-increment data
TRUNCATE TABLE operating.task_dependencies, operating.task_schedules, operating.tasks, operating.twelve_week_cycles, operating.weekly_commitments, operating.weekly_plans, strategy.initiatives, strategy.okr_cycles, strategy.okr_objectives, strategy.key_results, strategy.portfolios, strategy.projects, strategy.portfolio_projects CASCADE;

-- Drop bigserial defaults for all ID columns
ALTER TABLE operating.task_dependencies ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.task_schedules ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.tasks ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.twelve_week_cycles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.weekly_commitments ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.weekly_plans ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.initiatives ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.okr_cycles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.okr_objectives ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.key_results ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.portfolios ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.projects ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.portfolio_projects ALTER COLUMN id DROP DEFAULT;
