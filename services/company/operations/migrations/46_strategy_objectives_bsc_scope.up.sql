-- Migration 46: Strategic Objectives and BSC Focus Scopes

CREATE TABLE IF NOT EXISTS strategy.strategic_objectives (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  project_id            BIGINT,
  title                 TEXT NOT NULL,
  success_definition    TEXT,
  time_horizon_end      TIMESTAMPTZ,
  status                TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'ACTIVE', 'ARCHIVED')),
  owner_member_id       BIGINT,
  settings_revision     INTEGER,
  created_by_member_id  BIGINT,
  updated_by_member_id  BIGINT,
  revision              INTEGER NOT NULL DEFAULT 1,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_strategic_objectives_workspace UNIQUE (id, workspace_id),
  CONSTRAINT fk_strategic_objectives_project FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects (id, workspace_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS strategy.bsc_focus_scopes (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  strategic_objective_id BIGINT NOT NULL,
  perspective           TEXT NOT NULL CHECK (perspective IN ('FINANCIAL', 'CUSTOMER', 'INTERNAL_PROCESS', 'LEARNING_AND_GROWTH')),
  focus_question        TEXT,
  focus_statement       TEXT NOT NULL,
  priority              INTEGER NOT NULL DEFAULT 1,
  status                TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')),
  created_by_member_id  BIGINT,
  updated_by_member_id  BIGINT,
  revision              INTEGER NOT NULL DEFAULT 1,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_bsc_focus_scopes_objective FOREIGN KEY (strategic_objective_id, workspace_id)
    REFERENCES strategy.strategic_objectives (id, workspace_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_bsc_focus_scopes_active
  ON strategy.bsc_focus_scopes (strategic_objective_id, perspective)
  WHERE status = 'ACTIVE';
