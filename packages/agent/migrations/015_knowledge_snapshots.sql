-- Migration: 015_knowledge_snapshots.sql
-- Description: Bảng knowledge.snapshots — KnowledgeSnapshot artifact bất
--   biến (Wave M6). Additive — không đụng knowledge_sources/knowledge_chunks/
--   source_versions (migration 003 + 010). Snapshot chỉ THAM CHIẾU
--   source_id/version đã có qua content JSONB, không FK cứng tới
--   source_versions (1 snapshot có thể tham chiếu NHIỀU source_version cùng
--   lúc — quan hệ nhiều-nhiều không hợp với FK đơn giản trên 1 cột).
--
-- PRIMARY KEY (snapshot_id, version) — composite ngay từ đầu (khác
-- agent_evals.suites ở migration 008 vốn PK đơn cột do lịch sử, xem Wave M3
-- Task 5 comment về giới hạn đó) vì đây là bảng MỚI, không có ràng buộc kế
-- thừa nào.

CREATE TABLE IF NOT EXISTS knowledge.snapshots (
    snapshot_id VARCHAR(64) NOT NULL,
    version VARCHAR(32) NOT NULL,
    workspace_id VARCHAR(64) NOT NULL,
    definition_hash VARCHAR(64) NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (snapshot_id, version),
    CONSTRAINT uq_knowledge_snapshots_hash UNIQUE (snapshot_id, version, definition_hash)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_snapshots_workspace
    ON knowledge.snapshots(workspace_id);
