CREATE TABLE operating.execution_plans (
  id                      BIGINT PRIMARY KEY,
  workspace_id            BIGINT NOT NULL,
  project_id              BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
  weekly_plan_id          BIGINT REFERENCES operating.weekly_plans(id) ON DELETE SET NULL,
  goal_text               TEXT NOT NULL,
  status                  TEXT NOT NULL DEFAULT 'draft',
  origin                  TEXT NOT NULL,
  origin_ref              TEXT,
  run_id                  TEXT,
  accepted_by_member_id   BIGINT,
  accepted_at             TIMESTAMPTZ,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at              TIMESTAMPTZ
);

-- Chỉ một plan draft cho mỗi weekly_plan — phân rã lại thì plan cũ chuyển 'superseded'.
CREATE UNIQUE INDEX uix_execution_plans_one_draft_per_weekly_plan
  ON operating.execution_plans (weekly_plan_id)
  WHERE status = 'draft' AND deleted_at IS NULL;

CREATE INDEX ix_execution_plans_project_status
  ON operating.execution_plans (project_id, status) WHERE deleted_at IS NULL;

CREATE TABLE operating.execution_plan_items (
  id                      BIGINT PRIMARY KEY,
  plan_id                 BIGINT NOT NULL REFERENCES operating.execution_plans(id) ON DELETE CASCADE,
  workspace_id            BIGINT NOT NULL,
  title                   TEXT NOT NULL,
  decision_reason         TEXT NOT NULL,
  evidence_refs           JSONB NOT NULL DEFAULT '[]'::jsonb,
  owner_agent_profile     TEXT,
  expected_capability     TEXT,
  autonomy_class          TEXT NOT NULL,
  autonomy_class_source   TEXT NOT NULL,
  priority                TEXT DEFAULT 'medium',
  depends_on_item_ids     JSONB DEFAULT '[]'::jsonb,
  sort_key                DOUBLE PRECISION,
  materialized_task_id    BIGINT REFERENCES operating.tasks(id) ON DELETE SET NULL,
  status                  TEXT NOT NULL DEFAULT 'proposed',
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_execution_plan_items_plan ON operating.execution_plan_items (plan_id);
CREATE INDEX ix_execution_plan_items_materialized_task ON operating.execution_plan_items (materialized_task_id)
  WHERE materialized_task_id IS NOT NULL;
