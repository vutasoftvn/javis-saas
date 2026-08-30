-- 001_academy_programs.down.sql
-- Rollback Academy schema — drops all Academy tables in reverse dependency order.

DROP TABLE IF EXISTS academy.template_exports;
DROP TABLE IF EXISTS academy.simulation_runs;
DROP TABLE IF EXISTS academy.lesson_attempts;
DROP TABLE IF EXISTS academy.enrollments;
DROP TABLE IF EXISTS academy.lessons;
DROP TABLE IF EXISTS academy.modules;
DROP TABLE IF EXISTS academy.programs;

DROP SCHEMA IF EXISTS academy;
