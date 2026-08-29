-- services/company/operations/migrations/21_next_best_actions.up.sql
CREATE TABLE IF NOT EXISTS strategy.next_best_actions (
  id                  BIGINT PRIMARY KEY,
  workspace_id        BIGINT NOT NULL,
  source              TEXT NOT NULL CHECK (source IN ('evidence','finance','legal','stage')),
  recommendation      TEXT NOT NULL,
  priority            INTEGER NOT NULL DEFAULT 1,
  due_by              DATE,
  status              TEXT NOT NULL DEFAULT 'PROPOSED'
                        CHECK (status IN ('PROPOSED','ACCEPTED','REJECTED','DONE')),
  capability_required TEXT,
  decision_reason     TEXT NOT NULL,
  context_snapshot    JSONB NOT NULL DEFAULT '{}'::jsonb,
  evidence_refs       JSONB NOT NULL DEFAULT '[]'::jsonb,
  regulation_refs     JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_next_best_actions_ws_status_priority
  ON strategy.next_best_actions(workspace_id, status, priority);
