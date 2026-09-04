-- Kickoff wizard Bước 3 — AI gợi ý outcome + việc tuần đầu (spec
-- docs/superpowers/specs/2026-09-04-kickoff-step3-ai-suggestion-design.md).
-- Company điều phối round-trip company<->apps/cosa; ghi đè trực tiếp lên
-- draft, không lưu lịch sử nhiều lần gợi ý (ngoài phạm vi §11).
ALTER TABLE strategy.project_operating_setups
  ADD COLUMN ai_suggestion_status TEXT NULL
    CHECK (ai_suggestion_status IN ('dispatched', 'completed', 'failed')),
  ADD COLUMN ai_suggestion_run_id TEXT NULL,
  ADD COLUMN ai_suggested_outcome TEXT NULL,
  ADD COLUMN ai_suggested_actions JSONB NULL,
  ADD COLUMN ai_suggestion_requested_at TIMESTAMPTZ NULL;
