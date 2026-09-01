CREATE TABLE strategy.project_operating_setups (
  project_id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  status TEXT NOT NULL DEFAULT 'NOT_STARTED'
    CHECK (status IN ('NOT_STARTED', 'IN_PROGRESS', 'ACTIVE')),
  target_customer TEXT NULL,
  problem_statement TEXT NULL,
  evidence_level TEXT NULL
    CHECK (evidence_level IN ('NONE', 'ONE_TO_FOUR_INTERVIEWS', 'FIVE_PLUS_INTERVIEWS', 'PROTOTYPE_OR_REVENUE')),
  recommended_stage TEXT NULL
    CHECK (recommended_stage IN ('P0_DISCOVERY', 'P1_PROBLEM_VALIDATION')),
  selected_stage TEXT NULL
    CHECK (selected_stage IN ('P0_DISCOVERY', 'P1_PROBLEM_VALIDATION')),
  stage_duration_weeks INTEGER NULL CHECK (stage_duration_weeks BETWEEN 1 AND 4),
  stage_target_date TIMESTAMPTZ NULL,
  weekly_review_weekday SMALLINT NULL CHECK (weekly_review_weekday BETWEEN 1 AND 7),
  weekly_review_time TEXT NULL CHECK (weekly_review_time ~ '^([01][0-9]|2[0-3]):[0-5][0-9]$'),
  first_week_outcome TEXT NULL,
  first_week_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX idx_project_operating_setups_workspace_status
  ON strategy.project_operating_setups(workspace_id, status, updated_at DESC);
