-- services/company/operations/migrations/19_venture_stage_and_profile.up.sql
CREATE TABLE IF NOT EXISTS strategy.venture_profiles (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL UNIQUE,
  problem_statement     TEXT,
  target_customer       TEXT,
  industry              TEXT,
  geography             TEXT,
  currency              TEXT DEFAULT 'VND',
  timezone              TEXT DEFAULT 'Asia/Ho_Chi_Minh',
  founder_goal          VARCHAR(50),
  initial_runway_months INTEGER,
  stage_entered_at      TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_venture_profiles_workspace
  ON strategy.venture_profiles(workspace_id);

CREATE TABLE IF NOT EXISTS strategy.venture_stage_transitions (
  id               BIGINT PRIMARY KEY,
  workspace_id     BIGINT NOT NULL,
  from_stage       VARCHAR(50) NOT NULL,
  to_stage         VARCHAR(50) NOT NULL,
  reason           TEXT NOT NULL,
  actor_member_id  BIGINT,
  override_flag    BOOLEAN NOT NULL DEFAULT false,
  decided_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_venture_stage_transitions_ws_decided
  ON strategy.venture_stage_transitions(workspace_id, decided_at);
