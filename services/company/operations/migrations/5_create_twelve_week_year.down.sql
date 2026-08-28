-- Rollback 5_create_twelve_week_year.up.sql
DROP TABLE IF EXISTS operating.weekly_commitments CASCADE;
DROP TABLE IF EXISTS operating.weekly_plans CASCADE;
DROP TABLE IF EXISTS operating.twelve_week_cycles CASCADE;
