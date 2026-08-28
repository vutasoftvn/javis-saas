-- Rollback 6_create_projects_portfolios.up.sql
DROP TABLE IF EXISTS strategy.portfolio_projects CASCADE;
DROP TABLE IF EXISTS strategy.projects CASCADE;
DROP TABLE IF EXISTS strategy.portfolios CASCADE;
