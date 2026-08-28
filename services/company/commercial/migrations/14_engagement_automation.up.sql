-- P3: deterministic automation — rule typed/versioned + ledger idempotency + delayed schedule.
CREATE TABLE engagement.engagement_automation_rules (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  rule_key TEXT NOT NULL,                      -- ổn định qua các version
  version INTEGER NOT NULL DEFAULT 1,
  name TEXT NOT NULL,
  trigger TEXT NOT NULL,                       -- thread_opened | message_received | thread_status_changed | csat_recorded | time_sweep
  priority INTEGER NOT NULL DEFAULT 100,       -- nhỏ chạy trước
  condition JSONB NOT NULL,                    -- predicate tree typed
  actions JSONB NOT NULL,                      -- array typed action
  enabled BOOLEAN NOT NULL DEFAULT false,      -- fail-closed: rule mới off cho tới khi bật
  stop_on_match BOOLEAN NOT NULL DEFAULT false,
  effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  effective_until TIMESTAMPTZ,
  created_by_workforce_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_engagement_automation_rules_ver
  ON engagement.engagement_automation_rules(workspace_id, rule_key, version);
CREATE INDEX idx_engagement_automation_rules_trigger
  ON engagement.engagement_automation_rules(workspace_id, trigger, enabled, priority);

CREATE TABLE engagement.engagement_automation_applications (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  rule_key TEXT NOT NULL,
  rule_version INTEGER NOT NULL,
  thread_id BIGINT NOT NULL,
  trigger TEXT NOT NULL,
  action_index INTEGER NOT NULL,
  action_type TEXT NOT NULL,
  dedupe_key TEXT NOT NULL DEFAULT '',
  outcome TEXT NOT NULL,                       -- applied | skipped_condition_changed | skipped_ownership_changed | skipped_rule_disabled | skipped_no_authority | error
  detail JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_engagement_automation_applications
  ON engagement.engagement_automation_applications(rule_key, rule_version, thread_id, action_index, dedupe_key);
CREATE INDEX idx_engagement_automation_applications_thread
  ON engagement.engagement_automation_applications(thread_id, created_at);

CREATE TABLE engagement.engagement_automation_schedules (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  rule_key TEXT NOT NULL,
  rule_version INTEGER NOT NULL,
  thread_id BIGINT NOT NULL,
  action_index INTEGER NOT NULL,
  action JSONB NOT NULL,                       -- snapshot action delayed
  condition JSONB NOT NULL,                    -- snapshot condition phải still-true khi đến hạn
  due_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',      -- pending | done | skipped | error
  skip_reason TEXT,
  claimed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_engagement_automation_schedules_due
  ON engagement.engagement_automation_schedules(status, due_at);

-- CSAT trên outcome
ALTER TABLE engagement.engagement_thread_outcomes
  ADD COLUMN IF NOT EXISTS csat_score INTEGER,
  ADD COLUMN IF NOT EXISTS csat_recorded_at TIMESTAMPTZ;
