-- 001_academy_programs.up.sql
-- Academy schema migration — completely isolated from production lifecycle tables.
-- No foreign keys into strategy.projects, evidence, gate_evaluations, tasks, pilots,
-- metric_contracts, or capability_enablements.

CREATE SCHEMA IF NOT EXISTS academy;

CREATE TABLE IF NOT EXISTS academy.programs (
  id BIGINT PRIMARY KEY,
  slug VARCHAR(100) NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT,
  version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
  module_count INTEGER NOT NULL DEFAULT 0,
  lesson_count INTEGER NOT NULL DEFAULT 0,
  published BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS academy.modules (
  id BIGINT PRIMARY KEY,
  program_id BIGINT NOT NULL REFERENCES academy.programs(id) ON DELETE CASCADE,
  slug VARCHAR(100) NOT NULL,
  title TEXT NOT NULL,
  "order" INTEGER NOT NULL DEFAULT 0,
  learning_objective TEXT,
  lifecycle_topic VARCHAR(100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS academy.lessons (
  id BIGINT PRIMARY KEY,
  module_id BIGINT NOT NULL REFERENCES academy.modules(id) ON DELETE CASCADE,
  slug VARCHAR(100) NOT NULL,
  title TEXT NOT NULL,
  "order" INTEGER NOT NULL DEFAULT 0,
  practice_type VARCHAR(50) NOT NULL DEFAULT 'reading',
  content TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enrollments link to workspace/account only — NOT to any project or evidence record
CREATE TABLE IF NOT EXISTS academy.enrollments (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  account_id BIGINT NOT NULL,
  program_id BIGINT NOT NULL REFERENCES academy.programs(id) ON DELETE CASCADE,
  completed_lessons INTEGER NOT NULL DEFAULT 0,
  status VARCHAR(30) NOT NULL DEFAULT 'NOT_STARTED', -- NOT_STARTED|IN_PROGRESS|COMPLETED
  enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Lesson attempts carry synthetic=true; score is a learning rubric only, NOT a PMF metric
CREATE TABLE IF NOT EXISTS academy.lesson_attempts (
  id BIGINT PRIMARY KEY,
  enrollment_id BIGINT NOT NULL REFERENCES academy.enrollments(id) ON DELETE CASCADE,
  lesson_id BIGINT NOT NULL REFERENCES academy.lessons(id) ON DELETE CASCADE,
  status VARCHAR(30) NOT NULL DEFAULT 'NOT_STARTED',
  reflection TEXT,
  score INTEGER,
  synthetic BOOLEAN NOT NULL DEFAULT TRUE,
  attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Simulation runs: artifact_ref must start with 'academy-artifact://'
CREATE TABLE IF NOT EXISTS academy.simulation_runs (
  id BIGINT PRIMARY KEY,
  enrollment_id BIGINT NOT NULL REFERENCES academy.enrollments(id) ON DELETE CASCADE,
  scenario_ref TEXT NOT NULL,
  scenario_version VARCHAR(20) NOT NULL,
  artifact_ref TEXT NOT NULL, -- enforced: starts with 'academy-artifact://'
  synthetic BOOLEAN NOT NULL DEFAULT TRUE,
  feedback JSONB,
  disclaimer TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Template exports: one-way, human-confirmed, live_artifact_kind = 'academy_template_draft'
-- ineligible for evidence until human replaces sources
CREATE TABLE IF NOT EXISTS academy.template_exports (
  id BIGINT PRIMARY KEY,
  simulation_run_id BIGINT REFERENCES academy.simulation_runs(id) ON DELETE SET NULL,
  workspace_id BIGINT NOT NULL,
  account_id BIGINT NOT NULL,
  template_kind VARCHAR(80) NOT NULL,
  body JSONB NOT NULL,
  academy_source_ref TEXT NOT NULL, -- starts with 'academy-artifact://'
  disclaimer TEXT NOT NULL,
  live_artifact_kind VARCHAR(60) NOT NULL DEFAULT 'academy_template_draft',
  exported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  confirmed_by_account_id BIGINT NOT NULL
);
