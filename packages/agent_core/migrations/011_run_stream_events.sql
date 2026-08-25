-- Migration: 011_run_stream_events.sql
-- Description: Durable SSE fanout event log cho apps/cosa, thay thế in-memory
-- `_history` dict tại apps/cosa/api/event_stream.py::CosaEventStreamManager
-- (COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md §7, §29.6 Phase 5).
--
-- KHÔNG dùng chung agent_core.run_events (migration 001) dù tài liệu gốc §7.2
-- đề xuất — phát hiện khi implement: OpenAIAgentsKernel đã tự ghi vào
-- agent_core.run_events với vocabulary generic riêng của nó (run.started,
-- run.completed{final_output}, run.failed, tool.started, tool.completed,
-- run.waiting, run.resumed — xem packages/agent_core/kernel/
-- openai_agents_kernel.py::_emit_event). apps/cosa SSE layer dùng vocabulary
-- UX-cấp-app khác (reasoning.status, message.started, message.delta,
-- approval.required, approval.resolved) VÀ MỘT SỐ TÊN TRÙNG (run.started,
-- run.completed, run.failed) nhưng payload shape KHÁC (vd. run.completed:
-- kernel {"final_output":...} vs app {"output":...,"status":"COMPLETED"}).
-- Ghi chung 1 bảng sẽ tạo duplicate/xung đột event cho cùng run_id khi
-- replay, và đổi vocabulary/payload app-facing để tránh trùng là thay đổi
-- hợp đồng SSE với frontend (Flutter) — không thể verify an toàn trong phiên
-- này (không có môi trường chạy Flutter/browser). Bảng riêng ở schema
-- agent_conversation (đã có từ migration 006, cùng "apps/cosa-facing durable
-- substrate") giữ nguyên contract SSE hiện tại 100%, chỉ đổi persistence
-- layer từ RAM sang Postgres — không phải "nhân bản kiến trúc" (CLAUDE.md #4)
-- vì đây là 2 concern khác nhau: agent_core.run_events = kernel governance/
-- audit ledger; run_stream_events = app UX fanout log.

-- `sequence` là BIGSERIAL toàn cục (không reset theo từng run_id) — cùng
-- pattern đã proven ở agent_core.run_events.sequence_no (migration 001):
-- tránh hoàn toàn race condition khi tính "MAX(sequence)+1 theo run_id" dưới
-- concurrent insert, Postgres tự đảm bảo an toàn. Vẫn đủ để dùng làm cursor
-- "since_sequence"/Last-Event-ID cho 1 run cụ thể vì chỉ cần đơn điệu tăng
-- TRONG PHẠM VI 1 run_id, không cần liên tục từ 1.
CREATE TABLE IF NOT EXISTS agent_conversation.run_stream_events (
    sequence BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    conversation_id VARCHAR(64) NOT NULL,
    correlation_id VARCHAR(64),
    schema_version SMALLINT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_run_stream_events_run_seq
    ON agent_conversation.run_stream_events(run_id, sequence);
CREATE INDEX IF NOT EXISTS idx_run_stream_events_conversation
    ON agent_conversation.run_stream_events(conversation_id);
