-- services/company/operations/migrations/23_task_execution_records.up.sql
CREATE TABLE IF NOT EXISTS operating.task_execution_records (
  id                  BIGINT PRIMARY KEY,
  workspace_id        BIGINT NOT NULL,
  task_id             BIGINT NOT NULL REFERENCES operating.tasks(id) ON DELETE CASCADE,
  run_id              TEXT,
  tool_call_id        TEXT,
  capability_id       TEXT NOT NULL,
  triggered_by_kind   TEXT NOT NULL CHECK (triggered_by_kind IN ('agent','founder','workflow','system')),
  decision_record_id  BIGINT REFERENCES strategy.decision_records(id) ON DELETE SET NULL,
  status              TEXT NOT NULL DEFAULT 'SUCCESS'
                        CHECK (status IN ('SUCCESS','FAILED')),
  error_details       JSONB,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_task_execution_records_ws_task
  ON operating.task_execution_records(workspace_id, task_id);
