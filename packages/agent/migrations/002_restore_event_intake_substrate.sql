-- Task 0 — Khôi phục event-intake substrate bị đợt squash baseline Founder Trial
-- R1 (commit 81461673) xoá khỏi migration history NHƯNG code đang chạy vẫn phụ thuộc:
--   * apps/cosa/events/inbox.py       (INSERT INTO event_inbox — statement đầu tiên
--                                      của router.py::handle_event)
--   * apps/cosa/events/run_counter.py (đọc event_inbox theo aggregate/ngày)
--   * apps/cosa/events/rule_store.py  (PostgresTriggerRuleStore → event_trigger_rules)
--
-- State PHẲNG cuối cùng của: 019_event_inbox + 020_event_trigger_rules
-- (gồm cả ALTER event_inbox ADD aggregate_type/aggregate_id) +
-- 024_grant_event_tables_to_agent_app.
--
-- Bảng nằm ở schema `public` như bản gốc (runtime query không schema-qualify).
-- _grant_application_access trong packages/agent/scripts/migrate.py CỐ TÌNH bỏ
-- qua `public`, nên phải GRANT tường minh cho agent_app ở đây.

CREATE TABLE IF NOT EXISTS public.event_inbox (
  id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  workspace_id      TEXT        NOT NULL,
  event_id          UUID        NOT NULL,
  consumer_name     TEXT        NOT NULL,
  event_type        TEXT        NOT NULL,
  correlation_id    TEXT        NOT NULL,
  received_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  outcome           TEXT        NOT NULL,
  scheduled_task_id TEXT,
  aggregate_type    TEXT,
  aggregate_id      TEXT,
  UNIQUE (workspace_id, event_id, consumer_name)
);
CREATE INDEX IF NOT EXISTS idx_event_inbox_correlation
  ON public.event_inbox (workspace_id, correlation_id);
CREATE INDEX IF NOT EXISTS idx_event_inbox_agg_day
  ON public.event_inbox (workspace_id, aggregate_id, received_at);

CREATE TABLE IF NOT EXISTS public.event_trigger_rules (
  rule_id                        TEXT PRIMARY KEY,
  workspace_id                   TEXT        NOT NULL,
  event_type                     TEXT        NOT NULL,
  agent_spec_id                  TEXT        NOT NULL,
  agent_spec_version             TEXT        NOT NULL,
  agent_spec_hash                TEXT        NOT NULL,
  mode                           TEXT        NOT NULL
                                   CHECK (mode IN ('artifact_only', 'proposal', 'write')),
  max_runs_per_aggregate_per_day INTEGER     NOT NULL DEFAULT 1,
  required_capabilities          JSONB       NOT NULL DEFAULT '[]'::jsonb,
  aggregate_filter               JSONB,
  owner                          TEXT        NOT NULL DEFAULT 'operator',
  enabled                        BOOLEAN     NOT NULL DEFAULT false,
  eval_evidence_ref              TEXT,
  event_schema_version           INTEGER     NOT NULL DEFAULT 1,
  created_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, event_type)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.event_inbox         TO agent_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.event_trigger_rules TO agent_app;
