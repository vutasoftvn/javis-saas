-- Rollback 14_project_link_tables.up.sql
DROP TABLE IF EXISTS strategy.okr_objective_projects CASCADE;
DROP TABLE IF EXISTS operating.task_projects CASCADE;
