-- 017_model_run_usage.sql
--
-- Sổ cái usage LLM theo run (review 2026-09-27, G-3). Trước đây token chỉ vào
-- metric Prometheus nên không enforce được ngân sách theo workspace/profile.
-- Mỗi lần kernel chạy/resume xong ghi 1 dòng: token + chi phí ước tính (NULL
-- khi không biết giá model) theo profile THẬT đã dùng (kể cả fallback).
-- Chỉ Expand, idempotent. Lọc workspace_id tường minh trong WHERE (cùng mẫu
-- models.model_provider_profiles).

CREATE TABLE IF NOT EXISTS models.run_usage (
  usage_id          uuid PRIMARY KEY,
  workspace_id      text NOT NULL,
  project_id        text,
  run_id            text NOT NULL,
  agent_spec_id     text,
  profile_id        text NOT NULL,
  provider_type     text,
  model_id          text,
  prompt_tokens     integer NOT NULL DEFAULT 0 CHECK (prompt_tokens >= 0),
  completion_tokens integer NOT NULL DEFAULT 0 CHECK (completion_tokens >= 0),
  cost_usd          numeric(14, 6) CHECK (cost_usd IS NULL OR cost_usd >= 0),
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_run_usage_workspace_time
  ON models.run_usage (workspace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_run_usage_workspace_profile_time
  ON models.run_usage (workspace_id, profile_id, created_at DESC);
