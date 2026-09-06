-- Migration 45: Workspace Strategy Settings

CREATE TABLE IF NOT EXISTS strategy.workspace_strategy_settings (
  workspace_id              BIGINT PRIMARY KEY REFERENCES core.workspaces(id) ON DELETE CASCADE,
  strategy_method           TEXT NOT NULL DEFAULT 'CLASSIC' CHECK (strategy_method IN ('CLASSIC', 'BSC_FILTER')),
  bsc_mode                  TEXT NOT NULL DEFAULT 'OFF' CHECK (bsc_mode IN ('OFF', 'OPTIONAL', 'REQUIRED')),
  enabled_bsc_perspectives  JSONB NOT NULL DEFAULT '[]'::jsonb,
  tows_selection_limit      SMALLINT NOT NULL DEFAULT 1 CHECK (tows_selection_limit BETWEEN 1 AND 2),
  weekly_review_enabled     BOOLEAN NOT NULL DEFAULT true,
  mid_cycle_review_policy   TEXT NOT NULL DEFAULT 'AUTO' CHECK (mid_cycle_review_policy IN ('OFF', 'AUTO', 'CUSTOM')),
  end_cycle_review_enabled  BOOLEAN NOT NULL DEFAULT true,
  allowed_agent_profiles    JSONB NOT NULL DEFAULT '[]'::jsonb,
  approval_policy           TEXT NOT NULL DEFAULT 'FOUNDER_ONLY' CHECK (approval_policy IN ('FOUNDER_ONLY', 'DELEGATED_APPROVER')),
  revision                  INTEGER NOT NULL DEFAULT 1,
  updated_by_member_id      BIGINT,
  updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
