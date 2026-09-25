-- 016_restore_workforce_schedule_binding_upload_ticket.sql
--
-- 3 bảng runtime còn thiếu sau baseline clean-slate 001 (đối chiếu toàn bộ
-- `schema.table` mà code Python truy vấn với DB đã migrate):
--   * agent.workforce_schedules       — PostgresWorkforceRepository.create/get/
--     list_schedule, route /agent/workforce/schedules*
--   * agent.outcome_analysis_bindings — PostgresWorkforceRepository.get/upsert_
--     outcome_analysis_binding
--   * agent.local_upload_tickets      — PostgresUploadTicketRepository
--     (knowledge_ingestion/dependencies.py chọn khi có AGENT_DATABASE_URL)
--
-- Cột lấy đúng theo SQL của các repository. Chỉ Expand, idempotent.
-- RLS: chỉ local_upload_tickets (repository có set cosa.workspace_id). Bảng
-- workforce_* hiện có đều không bật RLS và repository không set context, nên
-- 2 bảng workforce mới giữ cùng mẫu (lọc workspace_id tường minh trong WHERE).

-- ============================================================================
-- agent.workforce_schedules
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent.workforce_schedules (
  schedule_id     uuid PRIMARY KEY,
  workspace_id    text NOT NULL,
  name            text NOT NULL,
  functional_key  text NOT NULL,
  cron_expression text NOT NULL,
  input_payload   jsonb NOT NULL DEFAULT '{}'::jsonb,
  configured_by   text NOT NULL,
  status          text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'RETIRED')),
  created_at      timestamptz NOT NULL DEFAULT now(),
  retired_at      timestamptz
);
CREATE INDEX IF NOT EXISTS idx_workforce_schedules_workspace_status
  ON agent.workforce_schedules (workspace_id, status, created_at);

-- ============================================================================
-- agent.outcome_analysis_bindings  (1 analyst/workspace/analysis_kind)
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent.outcome_analysis_bindings (
  workspace_id          text NOT NULL,
  analysis_kind         text NOT NULL,
  analyst_employee_id   uuid NOT NULL
    REFERENCES agent.workforce_employees (agent_instance_id),
  analyst_assignment_id uuid NOT NULL
    REFERENCES agent.workforce_assignments (assignment_id),
  policy                text NOT NULL,
  skill_id              text NOT NULL,
  skill_version         text NOT NULL,
  definition_hash       text NOT NULL,
  -- Tăng mỗi lần upsert (ON CONFLICT ... version + 1).
  version               integer NOT NULL DEFAULT 1,
  updated_by            text NOT NULL,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, analysis_kind)
);

-- ============================================================================
-- agent.local_upload_tickets
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent.local_upload_tickets (
  workspace_id             text NOT NULL,
  upload_id                text NOT NULL,
  -- Chỉ lưu SHA-256 của ticket secret, không lưu secret thô.
  secret_hash              text NOT NULL,
  max_bytes                bigint NOT NULL CHECK (max_bytes > 0),
  expires_at               timestamptz NOT NULL,
  -- Đường dẫn nội bộ trong quarantine, không bao giờ trả ra HTTP response.
  quarantine_relative_path text NOT NULL,
  created_at               timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (workspace_id, upload_id)
);
CREATE INDEX IF NOT EXISTS idx_local_upload_tickets_expires
  ON agent.local_upload_tickets (expires_at);

ALTER TABLE agent.local_upload_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent.local_upload_tickets FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS local_upload_tickets_workspace_isolation ON agent.local_upload_tickets;
CREATE POLICY local_upload_tickets_workspace_isolation ON agent.local_upload_tickets
  USING ((workspace_id = current_setting('cosa.workspace_id'::text, true)))
  WITH CHECK ((workspace_id = current_setting('cosa.workspace_id'::text, true)));
