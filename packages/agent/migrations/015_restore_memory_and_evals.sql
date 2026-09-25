-- 015_restore_memory_and_evals.sql
--
-- Khôi phục 2 schema mà baseline clean-slate 001 đã bỏ ra nhưng code runtime
-- vẫn dùng:
--   * agent_memory.agent_memories  (packages/agent/memory/providers/postgres.py,
--     được storage_factory chọn qua MemoryService.for_production mỗi khi có
--     AGENT_DATABASE_URL)
--   * agent_evals.suites/cases/runs/results/promotion_evidence
--     (packages/agent/evals/repositories.py, promotion_repository.py; được
--     apps/cosa/events/deps.py dùng cho promotion evidence)
-- Thiếu schema -> các đường này lỗi UndefinedTableError trên Postgres.
--
-- Cột lấy đúng theo SQL của các repository. Chỉ Expand, idempotent.
-- KHÔNG bật RLS: 2 repository này không set cosa.workspace_id (memory lọc
-- workspace_id tường minh trong WHERE; evals là dữ liệu cấp platform, không
-- thuộc workspace) — FORCE RLS sẽ làm mọi truy vấn trả 0 row.

-- ============================================================================
-- agent_memory.agent_memories
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS agent_memory;

CREATE TABLE IF NOT EXISTS agent_memory.agent_memories (
  id                   text PRIMARY KEY,
  application_id       text,
  workspace_id         text NOT NULL,
  scope_type           text NOT NULL DEFAULT 'WORKSPACE',
  scope_id             text NOT NULL,
  agent_key            text NOT NULL,
  subject_type         text,
  subject_id           text,
  kind                 text NOT NULL
    CHECK (kind IN ('WORKING', 'EPISODIC', 'SEMANTIC', 'PROCEDURAL', 'ORGANIZATIONAL')),
  content              text NOT NULL,
  content_hash         text,
  importance           double precision NOT NULL DEFAULT 0.5
    CHECK (importance >= 0 AND importance <= 1),
  tags                 jsonb NOT NULL DEFAULT '[]'::jsonb,
  sensitivity          text NOT NULL DEFAULT 'normal',
  source_run_id        text,
  source_event_id      text,
  provenance           jsonb NOT NULL DEFAULT '{}'::jsonb,
  status               text NOT NULL DEFAULT 'ACTIVE'
    CHECK (status IN ('ACTIVE', 'SUPERSEDED', 'EXPIRED', 'RETRACTED', 'ARCHIVED')),
  valid_from           timestamptz,
  valid_until          timestamptz,
  supersedes_memory_id text,
  metadata             jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now()
);
-- Khớp search(): WHERE workspace_id + status [+ agent_key/kind] ORDER BY created_at DESC.
CREATE INDEX IF NOT EXISTS idx_agent_memories_workspace_status_created
  ON agent_memory.agent_memories (workspace_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_memories_workspace_agent
  ON agent_memory.agent_memories (workspace_id, agent_key);

-- ============================================================================
-- agent_evals.*
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS agent_evals;

-- 1 row/suite_id: khớp ON CONFLICT (suite_id) và giới hạn đã ghi trong
-- PostgresEvalRepository.publish_suite (nhiều version cùng tồn tại là việc sau).
CREATE TABLE IF NOT EXISTS agent_evals.suites (
  suite_id        text PRIMARY KEY,
  name            text NOT NULL,
  target_kind     text,
  target_id       text,
  description     text,
  version         text NOT NULL,
  -- Nullable: get_suite() có nhánh fallback cho row cũ chưa có hash/content.
  definition_hash text,
  content         jsonb,
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- Danh mục case của suite (evals/artifacts.py: EvalSuite chỉ tham chiếu ID
-- case có trong bảng này). results.case_id KHÔNG FK sang đây: runner ghi kết
-- quả cho case khai báo trong skillpack chưa chắc đã được seed vào bảng.
CREATE TABLE IF NOT EXISTS agent_evals.cases (
  case_id    text PRIMARY KEY,
  suite_id   text NOT NULL REFERENCES agent_evals.suites (suite_id) ON DELETE CASCADE,
  input      jsonb NOT NULL DEFAULT '{}'::jsonb,
  expected   jsonb NOT NULL DEFAULT '{}'::jsonb,
  metadata   jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_eval_cases_suite ON agent_evals.cases (suite_id);

CREATE TABLE IF NOT EXISTS agent_evals.runs (
  eval_run_id            text PRIMARY KEY,
  suite_id               text,
  target_kind            text NOT NULL,
  target_id              text NOT NULL,
  target_version         text,
  target_definition_hash text,
  suite_version          text,
  suite_definition_hash  text,
  status                 text NOT NULL DEFAULT 'running',
  pass_rate              double precision,
  started_at             timestamptz NOT NULL DEFAULT now(),
  completed_at           timestamptz
);
CREATE INDEX IF NOT EXISTS idx_eval_runs_target
  ON agent_evals.runs (target_kind, target_id, target_version);

CREATE TABLE IF NOT EXISTS agent_evals.results (
  result_id     text PRIMARY KEY,
  eval_run_id   text NOT NULL REFERENCES agent_evals.runs (eval_run_id) ON DELETE CASCADE,
  case_id       text NOT NULL,
  passed        boolean NOT NULL,
  score         double precision NOT NULL DEFAULT 0,
  details       text,
  error_message text,
  evaluated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_eval_results_run
  ON agent_evals.results (eval_run_id, evaluated_at);

CREATE TABLE IF NOT EXISTS agent_evals.promotion_evidence (
  evidence_id            text PRIMARY KEY,
  target_kind            text NOT NULL,
  target_id              text NOT NULL,
  target_version         text NOT NULL,
  target_definition_hash text NOT NULL,
  required_eval_run_ids  jsonb NOT NULL DEFAULT '[]'::jsonb,
  observed_fingerprints  jsonb NOT NULL DEFAULT '{}'::jsonb,
  policy_version         text NOT NULL,
  policy_checks_passed   boolean NOT NULL,
  check_details          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at             timestamptz NOT NULL DEFAULT now()
);
-- Khớp list_by_target(): lọc đủ 4 trường target, ORDER BY created_at.
CREATE INDEX IF NOT EXISTS idx_promotion_evidence_target
  ON agent_evals.promotion_evidence
     (target_kind, target_id, target_version, target_definition_hash, created_at);
