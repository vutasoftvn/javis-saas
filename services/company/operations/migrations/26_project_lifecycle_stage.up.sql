-- services/company/operations/migrations/26_project_lifecycle_stage.up.sql
-- M4 §3 — Project lifecycle P0..P6, ĐỘC LẬP với Workspace W0..W5.
--   strategy.projects.phase -> lifecycle_stage (enum P0_DISCOVERY..P6_SCALE_GOVERN)
--   + stage_version (CAS), stage_entered_at
--   status chuẩn hoá ACTIVE|PAUSED|COMPLETED|ARCHIVED
-- + journal riêng project_stage_transitions + policy riêng project_stage_transition_policies
--   (KHÔNG dùng chung workspace_stage_transitions / stage_transition_policies).

ALTER TABLE strategy.projects RENAME COLUMN phase TO lifecycle_stage;
ALTER TABLE strategy.projects
  ADD COLUMN IF NOT EXISTS stage_version    INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS stage_entered_at TIMESTAMPTZ;

-- Backfill: legacy project stage (LEGACY_PROJECT_STAGE_TO_CANONICAL) + legacy workspace
-- S-set + free text (PLANNING/execution/NULL) -> P0_DISCOVERY.
UPDATE strategy.projects SET lifecycle_stage = CASE lifecycle_stage
  WHEN 'S0_EXPLORE'             THEN 'P0_DISCOVERY'
  WHEN 'S1_PROBLEM_VALIDATION'  THEN 'P1_PROBLEM_VALIDATION'
  WHEN 'S2_SOLUTION_VALIDATION' THEN 'P2_SOLUTION_VALIDATION'
  WHEN 'S3_BUSINESS_VALIDATION' THEN 'P3_BUILD_VALIDATE'
  WHEN 'S3_MVP_BUILD'           THEN 'P3_BUILD_VALIDATE'
  WHEN 'S4_GO_TO_MARKET'        THEN 'P4_GO_TO_MARKET'
  WHEN 'S4_PRODUCT_MARKET_FIT'  THEN 'P4_GO_TO_MARKET'
  WHEN 'S5_OPERATE_GROWTH'      THEN 'P5_OPERATE_GROWTH'
  WHEN 'S5_SCALE'               THEN 'P5_OPERATE_GROWTH'
  WHEN 'S6_SCALE_GOVERN'        THEN 'P6_SCALE_GOVERN'
  WHEN 'P0_DISCOVERY'           THEN 'P0_DISCOVERY'
  WHEN 'P1_PROBLEM_VALIDATION'  THEN 'P1_PROBLEM_VALIDATION'
  WHEN 'P2_SOLUTION_VALIDATION' THEN 'P2_SOLUTION_VALIDATION'
  WHEN 'P3_BUILD_VALIDATE'      THEN 'P3_BUILD_VALIDATE'
  WHEN 'P4_GO_TO_MARKET'        THEN 'P4_GO_TO_MARKET'
  WHEN 'P5_OPERATE_GROWTH'      THEN 'P5_OPERATE_GROWTH'
  WHEN 'P6_SCALE_GOVERN'        THEN 'P6_SCALE_GOVERN'
  ELSE 'P0_DISCOVERY'
END;
UPDATE strategy.projects SET lifecycle_stage = 'P0_DISCOVERY' WHERE lifecycle_stage IS NULL;

ALTER TABLE strategy.projects ALTER COLUMN lifecycle_stage SET DEFAULT 'P0_DISCOVERY';
ALTER TABLE strategy.projects ALTER COLUMN lifecycle_stage SET NOT NULL;
ALTER TABLE strategy.projects
  ADD CONSTRAINT projects_lifecycle_stage_chk
  CHECK (lifecycle_stage IN (
    'P0_DISCOVERY','P1_PROBLEM_VALIDATION','P2_SOLUTION_VALIDATION',
    'P3_BUILD_VALIDATE','P4_GO_TO_MARKET','P5_OPERATE_GROWTH','P6_SCALE_GOVERN'
  ));

UPDATE strategy.projects SET status = CASE lower(status)
  WHEN 'active'    THEN 'ACTIVE'
  WHEN 'paused'    THEN 'PAUSED'
  WHEN 'completed' THEN 'COMPLETED'
  WHEN 'archived'  THEN 'ARCHIVED'
  ELSE 'ACTIVE'
END;
ALTER TABLE strategy.projects ALTER COLUMN status SET DEFAULT 'ACTIVE';
ALTER TABLE strategy.projects
  ADD CONSTRAINT projects_status_chk
  CHECK (status IN ('ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED'));

CREATE TABLE IF NOT EXISTS strategy.project_stage_transition_policies (
  id             BIGINT PRIMARY KEY,
  workspace_id   BIGINT NOT NULL,
  project_id     BIGINT,
  from_stage     VARCHAR(50) NOT NULL,
  to_stage       VARCHAR(50) NOT NULL,
  allowed        BOOLEAN NOT NULL DEFAULT true,
  policy_version TEXT NOT NULL DEFAULT 'v1',
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_project_stage_transition_policies_ws
  ON strategy.project_stage_transition_policies(workspace_id, project_id);

CREATE TABLE IF NOT EXISTS strategy.project_stage_transitions (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL,
  project_id            BIGINT NOT NULL,
  from_stage            VARCHAR(50) NOT NULL,
  to_stage              VARCHAR(50) NOT NULL,
  reason                TEXT NOT NULL,
  actor_member_id       BIGINT,
  actor_role            TEXT,
  override_flag         BOOLEAN NOT NULL DEFAULT false,
  override_approval_ref TEXT,
  source                TEXT NOT NULL DEFAULT 'manual',
  stage_version_from    INTEGER,
  policy_version        TEXT,
  evidence_snapshot     JSONB NOT NULL DEFAULT '{}'::jsonb,
  evaluation_result     JSONB,
  decided_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT project_stage_transitions_source_chk
    CHECK (source IN ('manual', 'autonomous', 'api', 'system'))
);
CREATE INDEX IF NOT EXISTS idx_project_stage_transitions_ws_proj_decided
  ON strategy.project_stage_transitions(workspace_id, project_id, decided_at);
