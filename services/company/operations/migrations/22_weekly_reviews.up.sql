-- services/company/operations/migrations/22_weekly_reviews.up.sql
CREATE TABLE IF NOT EXISTS strategy.weekly_reviews (
  id                  BIGINT PRIMARY KEY,
  workspace_id        BIGINT NOT NULL,
  week_start_date     DATE NOT NULL,
  summary             TEXT NOT NULL,
  stage_assessment    TEXT,
  cash_summary        TEXT,
  obligations_summary TEXT,
  action_proposals    JSONB NOT NULL DEFAULT '[]'::jsonb,
  status              TEXT NOT NULL DEFAULT 'DRAFT'
                        CHECK (status IN ('DRAFT','COMPLETED')),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, week_start_date)
);

CREATE INDEX IF NOT EXISTS idx_weekly_reviews_ws_date
  ON strategy.weekly_reviews(workspace_id, week_start_date);
