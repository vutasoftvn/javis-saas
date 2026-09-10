-- SP-A Task 5B — Khôi phục các bảng `operating.*` / `strategy.*` bị bỏ rơi
-- trong đợt squash baseline Founder Trial R1 (`81461673`).
--
-- Schema Drizzle (`services/company/shared/db/schema/operations.ts` +
-- `strategy.ts`) vẫn khai báo các bảng này và `operating` / `strategy` là 2
-- schema RETAINED của R1 (`test_founder_trial_baseline_inventory.py`), nhưng
-- `001_founder_trial_mvp_baseline.up.sql` không tạo chúng. `make e2e-test` khi
-- cô lập vào test DB fail vì `relation "operating.runtime_source_signals" does
-- not exist` và `operating.task_projects`.
--
-- Expand-only + idempotent: chỉ `CREATE TABLE IF NOT EXISTS` /
-- `CREATE INDEX IF NOT EXISTS`. Không INSERT/UPDATE/DELETE, không DROP/RENAME.
-- PK bigint do app cấp (Snowflake) — không IDENTITY, không default.
--
-- Nguồn DDL verbatim (đã làm idempotent):
--   * migration 14 `14_project_link_tables.up.sql`  -> operating.task_projects,
--     strategy.okr_objective_projects
--   * migration 33 `33_mvp_strategy_canvas_runtime.up.sql` -> strategy.canvases,
--     strategy.canvas_revisions, operating.runtime_source_signals,
--     operating.runtime_snoozes
--
-- Thứ tự: bảng cha trước bảng con. `operating.tasks`, `strategy.projects` do
-- `001` tạo sẵn (kèm `UNIQUE (id, workspace_id)` cho composite FK).

-- ---------------------------------------------------------------------------
-- Từ migration 33 — Strategy canvases + canvas revisions
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS strategy.canvases (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  name TEXT NOT NULL CHECK (length(trim(name)) > 0),
  description TEXT NULL,
  current_revision_id BIGINT NULL,
  created_by_member_id BIGINT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ NULL,
  UNIQUE (id, workspace_id)
);

CREATE TABLE IF NOT EXISTS strategy.canvas_revisions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  canvas_id BIGINT NOT NULL,
  parent_revision_id BIGINT NULL,
  content JSONB NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('DRAFT', 'IN_REVIEW', 'APPROVED', 'REJECTED')),
  origin TEXT NOT NULL CHECK (origin IN ('USER', 'MODEL_DRAFT')),
  source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_by_member_id BIGINT NULL,
  reviewed_by_member_id BIGINT NULL,
  review_note TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewed_at TIMESTAMPTZ NULL,
  UNIQUE (id, workspace_id),
  FOREIGN KEY (canvas_id, workspace_id) REFERENCES strategy.canvases(id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_strategy_canvases_workspace ON strategy.canvases(workspace_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_strategy_canvas_revisions_workspace ON strategy.canvas_revisions(workspace_id, canvas_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- Từ migration 33 — Runtime source signals + actor snoozes
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operating.runtime_source_signals (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  source_kind TEXT NOT NULL,
  source_id TEXT NOT NULL,
  sequence BIGINT NOT NULL,
  state TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  correlation_id TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, source_kind, source_id, sequence)
);

CREATE INDEX IF NOT EXISTS idx_runtime_source_signals_lookup ON operating.runtime_source_signals(workspace_id, source_kind, source_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS operating.runtime_snoozes (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  actor_member_id BIGINT NOT NULL,
  source_kind TEXT NOT NULL,
  source_id TEXT NOT NULL,
  snoozed_until TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, actor_member_id, source_kind, source_id)
);

CREATE INDEX IF NOT EXISTS idx_runtime_snoozes_actor ON operating.runtime_snoozes(workspace_id, actor_member_id, snoozed_until);

-- ---------------------------------------------------------------------------
-- Từ migration 14 — Bảng liên kết many-to-many Task/Objective <-> Project.
-- Composite FK (…, workspace_id) chặn liên kết chéo workspace ngay tầng DB.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operating.task_projects (
    workspace_id BIGINT NOT NULL,
    task_id      BIGINT NOT NULL,
    project_id   BIGINT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (task_id, project_id),
    CONSTRAINT fk_task_projects_task
      FOREIGN KEY (task_id, workspace_id)
      REFERENCES operating.tasks (id, workspace_id) ON DELETE CASCADE,
    CONSTRAINT fk_task_projects_project
      FOREIGN KEY (project_id, workspace_id)
      REFERENCES strategy.projects (id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_task_projects_workspace ON operating.task_projects(workspace_id);
CREATE INDEX IF NOT EXISTS idx_task_projects_project ON operating.task_projects(project_id);

-- LƯU Ý (deviation so với migration 14 gốc): FK `fk_okr_objective_projects_objective`
-- trỏ `strategy.okr_objectives (id, workspace_id)` bị BỎ vì `strategy.okr_objectives`
-- vẫn chưa nằm trong baseline R1 (thuộc gap lớn hơn — xem task-5B-report.md).
-- Schema Drizzle `strategySchema.table("okr_objective_projects")` không khai báo
-- FK nào nên cấu trúc dưới đây vẫn khớp Drizzle. Khi `strategy.okr_objectives`
-- được khôi phục, một migration sau sẽ thêm lại FK này.
CREATE TABLE IF NOT EXISTS strategy.okr_objective_projects (
    workspace_id BIGINT NOT NULL,
    objective_id BIGINT NOT NULL,
    project_id   BIGINT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (objective_id, project_id),
    CONSTRAINT fk_okr_objective_projects_project
      FOREIGN KEY (project_id, workspace_id)
      REFERENCES strategy.projects (id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_okr_objective_projects_workspace ON strategy.okr_objective_projects(workspace_id);
CREATE INDEX IF NOT EXISTS idx_okr_objective_projects_project ON strategy.okr_objective_projects(project_id);
