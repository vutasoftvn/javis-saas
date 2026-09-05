-- services/company/operations/migrations/42_execution_cycle_calendar.up.sql
-- S2: Configurable execution cycles, civil calendar dates, and revision tracking

ALTER TABLE operating.twelve_week_cycles
  ADD COLUMN IF NOT EXISTS display_name VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS timezone VARCHAR(100) NOT NULL DEFAULT 'UTC',
  ADD COLUMN IF NOT EXISTS start_local_date DATE NULL,
  ADD COLUMN IF NOT EXISTS end_local_date_exclusive DATE NULL,
  ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS calendar_state VARCHAR(50) NOT NULL DEFAULT 'READY';

-- Backfill existing rows: if start_date exists, derive local dates; otherwise mark NEEDS_SETUP
UPDATE operating.twelve_week_cycles
SET
  start_local_date = (start_date AT TIME ZONE 'UTC')::date,
  end_local_date_exclusive = (start_date AT TIME ZONE 'UTC')::date + (COALESCE(duration_weeks, 12) * 7),
  calendar_state = 'READY'
WHERE start_date IS NOT NULL AND start_local_date IS NULL;

UPDATE operating.twelve_week_cycles
SET calendar_state = 'NEEDS_SETUP'
WHERE start_date IS NULL AND start_local_date IS NULL;

-- Allow flexible cycle duration in project operating setup
ALTER TABLE strategy.project_operating_setups
  ADD COLUMN IF NOT EXISTS cycle_duration_weeks INTEGER NULL;

-- Add source tracking and revision to weekly commitments
ALTER TABLE operating.weekly_commitments
  ADD COLUMN IF NOT EXISTS source_action_id VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS source_revision INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;

-- Add source tracking and revision to tasks
ALTER TABLE operating.tasks
  ADD COLUMN IF NOT EXISTS source_action_id VARCHAR(255) NULL,
  ADD COLUMN IF NOT EXISTS source_revision INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;

-- Create cycle_revisions table for audit trail of cycle mutations/resizing
CREATE TABLE IF NOT EXISTS operating.cycle_revisions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  cycle_id BIGINT NOT NULL REFERENCES operating.twelve_week_cycles(id) ON DELETE CASCADE,
  revision INTEGER NOT NULL,
  before_state JSONB NOT NULL,
  after_state JSONB NOT NULL,
  reason TEXT NULL,
  actor_id TEXT NULL,
  actor_kind TEXT NOT NULL DEFAULT 'user',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (cycle_id, revision)
);

CREATE INDEX IF NOT EXISTS idx_cycle_revisions_ws_cycle
  ON operating.cycle_revisions(workspace_id, cycle_id, revision DESC);
