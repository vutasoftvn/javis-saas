-- 014_local_ingestion_state.sql
--
-- State machine ingestion cục bộ (apps/cosa/knowledge_ingestion/local_repository.py,
-- LocalIngestionRepository). Baseline clean-slate 001 không có 2 bảng này, nhưng
-- knowledge_ingestion/dependencies.py chọn LocalIngestionRepository mỗi khi có
-- AGENT_DATABASE_URL -> upload/claim/publish tài liệu lỗi UndefinedTableError.
--
-- Cột lấy đúng theo SQL của repository. Chỉ Expand, idempotent. RLS theo
-- cosa.workspace_id (fail-closed) như knowledge.* / vault.*.

CREATE TABLE IF NOT EXISTS agent.local_ingestion_attempts (
  workspace_id             text NOT NULL,
  upload_id                text NOT NULL,
  state                    text NOT NULL DEFAULT 'QUEUED'
    CHECK (state IN ('QUEUED', 'VALIDATING', 'CONVERTING', 'REVIEW_PENDING',
                     'PUBLISHED', 'REJECTED', 'FAILED')),
  -- Đường dẫn nội bộ trong quarantine, không bao giờ trả ra HTTP response.
  quarantine_relative_path text NOT NULL,
  declared_media_type      text,
  detected_media_type      text,
  source_sha256            text,
  size_bytes               bigint CHECK (size_bytes IS NULL OR size_bytes >= 0),
  -- Chỉ lưu SHA-256 của claim token (fencing), không lưu token thô.
  claim_token_hash         text,
  knowledge_source_id      text,
  manifest_json            jsonb,
  vault_document_id        text,
  vault_version_id         text,
  failure_code             text,
  created_by               text NOT NULL,
  created_at               timestamptz NOT NULL DEFAULT now(),
  updated_at               timestamptz NOT NULL DEFAULT now(),
  -- Khớp ON CONFLICT (workspace_id, upload_id) DO NOTHING trong create_queued.
  PRIMARY KEY (workspace_id, upload_id)
);
CREATE INDEX IF NOT EXISTS idx_local_ingestion_attempts_state
  ON agent.local_ingestion_attempts (workspace_id, state, updated_at DESC);

-- Nhật ký chuyển trạng thái append-only.
CREATE TABLE IF NOT EXISTS agent.local_ingestion_events (
  event_id     bigserial PRIMARY KEY,
  workspace_id text NOT NULL,
  upload_id    text NOT NULL,
  old_state    text,
  new_state    text NOT NULL,
  reason       text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_local_ingestion_events_attempt
    FOREIGN KEY (workspace_id, upload_id)
    REFERENCES agent.local_ingestion_attempts (workspace_id, upload_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_local_ingestion_events_attempt
  ON agent.local_ingestion_events (workspace_id, upload_id, created_at);

ALTER TABLE agent.local_ingestion_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent.local_ingestion_attempts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS local_ingestion_attempts_workspace_isolation ON agent.local_ingestion_attempts;
CREATE POLICY local_ingestion_attempts_workspace_isolation ON agent.local_ingestion_attempts
  USING ((workspace_id = current_setting('cosa.workspace_id'::text, true)))
  WITH CHECK ((workspace_id = current_setting('cosa.workspace_id'::text, true)));

ALTER TABLE agent.local_ingestion_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent.local_ingestion_events FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS local_ingestion_events_workspace_isolation ON agent.local_ingestion_events;
CREATE POLICY local_ingestion_events_workspace_isolation ON agent.local_ingestion_events
  USING ((workspace_id = current_setting('cosa.workspace_id'::text, true)))
  WITH CHECK ((workspace_id = current_setting('cosa.workspace_id'::text, true)));
