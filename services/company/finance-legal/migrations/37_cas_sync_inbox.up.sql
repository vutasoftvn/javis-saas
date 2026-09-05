-- Migration 37: cas_sync_inbox — hộp thư hợp nhất GET-poll + webhook Cas.so
-- F3: unify Cas.so GET-poll và webhook vào một pipeline ingestion bền, có
-- retry/backoff/DLQ. Expand-only: chỉ thêm cột/bảng, không xoá gì đã có.

-- 1. bank_connections: bổ sung sync coverage-start (điểm bắt đầu backfill
--    lịch sử đã hoàn tất) — sync_cursor/sync_error/sync_error_count/
--    sync_locked_until đã được thêm ở bản nháp trước, giữ nguyên ở đây để
--    migration này idempotent nếu chạy lại từ đầu trên DB mới.
ALTER TABLE finance.bank_connections
  ADD COLUMN IF NOT EXISTS sync_cursor TEXT,
  ADD COLUMN IF NOT EXISTS sync_error TEXT,
  ADD COLUMN IF NOT EXISTS sync_error_count INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS sync_locked_until TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS sync_coverage_start TIMESTAMPTZ;

-- 2. bank_transactions: ràng buộc duy nhất THẬT ở tầng DB cho
--    (bank_connection_id, external_transaction_id) — trước đây chỉ có
--    select-then-insert ở tầng app (race được dưới tải đồng thời / hai
--    worker cùng ingest). Đây là điều kiện tiên quyết để GET-poll và webhook
--    của cùng giao dịch luôn hội tụ về đúng 1 canonical row.
CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_transactions_conn_ext_unique
  ON finance.bank_transactions (bank_connection_id, external_transaction_id);

-- 3. cas_sync_inbox: hộp thư hợp nhất — mỗi dòng là 1 sự kiện thô (từ webhook
--    hoặc từ 1 giao dịch trong 1 trang GET-poll), dedup theo
--    (provider, environment, event_identity). event_identity dựng từ field
--    contract-defined (connection/grant + account + transaction id + loại
--    event + version contract) — KHÔNG dùng hash nguyên payload làm identity
--    (2 lần giao cùng 1 giao dịch có thể lệch byte nhưng phải cùng identity).
CREATE TABLE IF NOT EXISTS finance.cas_sync_inbox (
  id                  BIGINT PRIMARY KEY,
  bank_connection_id  BIGINT REFERENCES finance.bank_connections(id) ON DELETE CASCADE,
  provider            TEXT NOT NULL DEFAULT 'cas',
  environment         TEXT NOT NULL DEFAULT 'sandbox',
  source              TEXT NOT NULL, -- 'webhook' | 'poll'
  event_identity      TEXT NOT NULL,
  raw_payload         JSONB NOT NULL,
  status              TEXT NOT NULL DEFAULT 'RECEIVED', -- RECEIVED|PROCESSING|PROCESSED|FAILED|DLQ|QUARANTINED|IGNORED
  attempts            INT NOT NULL DEFAULT 0,
  next_attempt_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  lease_until         TIMESTAMPTZ,
  lease_token         TEXT,
  error_code          TEXT,
  error_msg           TEXT,
  bank_transaction_id BIGINT REFERENCES finance.bank_transactions(id) ON DELETE SET NULL,
  received_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at        TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cas_sync_inbox_dedup
  ON finance.cas_sync_inbox (provider, environment, event_identity);

-- Truy vấn "due" của worker: trạng thái cần xử lý + đến hạn thử lại +
-- không đang bị lease. Index thường (không partial trên lease_until vì so
-- sánh với now() không immutable) đủ cho cardinality dự kiến của bảng này.
CREATE INDEX IF NOT EXISTS idx_cas_sync_inbox_due
  ON finance.cas_sync_inbox (status, next_attempt_at, lease_until);

CREATE INDEX IF NOT EXISTS idx_cas_sync_inbox_conn
  ON finance.cas_sync_inbox (bank_connection_id, received_at DESC);

-- 4. cas_normalizer_log: audit trail chuyển đổi raw -> bank_transaction,
--    dedup nghiệp vụ thứ hai theo (bank_connection_id, provider_tx_id).
CREATE TABLE IF NOT EXISTS finance.cas_normalizer_log (
  id                    BIGINT PRIMARY KEY,
  bank_connection_id    BIGINT NOT NULL REFERENCES finance.bank_connections(id) ON DELETE CASCADE,
  inbox_event_id        BIGINT REFERENCES finance.cas_sync_inbox(id) ON DELETE SET NULL,
  provider_tx_id        TEXT NOT NULL,
  provider_tx_hash      TEXT NOT NULL,
  bank_transaction_id   BIGINT REFERENCES finance.bank_transactions(id) ON DELETE SET NULL,
  action                TEXT NOT NULL DEFAULT 'INSERT', -- INSERT|SKIP_DUP|CONFLICT|FAIL
  fail_reason           TEXT,
  normalized_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cas_normalizer_log_dedup
  ON finance.cas_normalizer_log (bank_connection_id, provider_tx_id);

CREATE INDEX IF NOT EXISTS idx_cas_normalizer_log_conn
  ON finance.cas_normalizer_log (bank_connection_id, normalized_at DESC);

-- 5. ingestion_dlq: inbox event thất bại quá số lần retry cho phép.
CREATE TABLE IF NOT EXISTS finance.ingestion_dlq (
  id                   BIGINT PRIMARY KEY,
  inbox_event_id       BIGINT NOT NULL REFERENCES finance.cas_sync_inbox(id),
  bank_connection_id   BIGINT REFERENCES finance.bank_connections(id),
  moved_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  fail_count           INT NOT NULL DEFAULT 0,
  last_error           TEXT,
  reviewed             BOOLEAN NOT NULL DEFAULT false,
  reviewed_at          TIMESTAMPTZ,
  reviewed_by          BIGINT
);

CREATE INDEX IF NOT EXISTS idx_ingestion_dlq_conn
  ON finance.ingestion_dlq (bank_connection_id, moved_at DESC);
