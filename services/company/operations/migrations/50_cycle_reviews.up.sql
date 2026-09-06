-- 50_cycle_reviews.up.sql
-- Table operating.cycle_reviews for weekly, mid-cycle, and end-cycle project/cycle reviews.

CREATE TABLE operating.cycle_reviews (
  id                      BIGINT PRIMARY KEY,
  workspace_id            BIGINT NOT NULL,
  project_id              BIGINT REFERENCES strategy.projects(id) ON DELETE SET NULL,
  cycle_id                BIGINT NOT NULL REFERENCES operating.twelve_week_cycles(id) ON DELETE CASCADE,
  kind                    VARCHAR(50) NOT NULL, -- 'WEEKLY' | 'MID_CYCLE' | 'END_CYCLE'
  scheduled_week_no       INTEGER NOT NULL,
  scheduled_at            TIMESTAMPTZ,
  status                  VARCHAR(50) NOT NULL DEFAULT 'SCHEDULED', -- 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'SKIPPED' | 'SUPERSEDED'
  kr_snapshots            JSONB NOT NULL DEFAULT '[]'::jsonb,
  initiative_snapshots    JSONB NOT NULL DEFAULT '[]'::jsonb,
  pestel_snapshots        JSONB NOT NULL DEFAULT '[]'::jsonb,
  decision_id             BIGINT REFERENCES strategy.decision_records(id) ON DELETE SET NULL,
  conclusion              TEXT,
  conducted_by_member_id  BIGINT,
  conducted_at            TIMESTAMPTZ,
  settings_revision       INTEGER,
  revision                INTEGER NOT NULL DEFAULT 1,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at              TIMESTAMPTZ
);

CREATE INDEX ix_cycle_reviews_workspace_cycle
  ON operating.cycle_reviews (workspace_id, cycle_id, scheduled_week_no, kind)
  WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX uix_cycle_reviews_active_slot
  ON operating.cycle_reviews (cycle_id, kind, scheduled_week_no)
  WHERE status NOT IN ('SUPERSEDED', 'SKIPPED') AND deleted_at IS NULL;
