-- Down Migration 014: state machine ingestion cục bộ.
-- Chỉ rollback khi chưa có attempt nào (không xoá lịch sử ingestion thật).

-- FORCE RLS làm owner cũng thấy 0 row khi thiếu cosa.workspace_id -> tắt FORCE
-- trước để phép kiểm tra "còn dữ liệu" là thật.
ALTER TABLE IF EXISTS agent.local_ingestion_attempts NO FORCE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF to_regclass('agent.local_ingestion_attempts') IS NOT NULL
     AND EXISTS (SELECT 1 FROM agent.local_ingestion_attempts LIMIT 1) THEN
    RAISE EXCEPTION 'Cannot rollback migration 014: local_ingestion_attempts contains data.';
  END IF;
END $$;

ALTER TABLE IF EXISTS agent.local_ingestion_attempts FORCE ROW LEVEL SECURITY;
DROP TABLE IF EXISTS agent.local_ingestion_events;
DROP TABLE IF EXISTS agent.local_ingestion_attempts;
