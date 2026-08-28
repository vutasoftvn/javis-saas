-- P1: Customer Support Copilot — enablement per workspace (fail-closed) + audit invocation.
CREATE TABLE engagement.engagement_copilot_settings (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT false,          -- fail-closed
  allowed_intents JSONB NOT NULL DEFAULT '["summarize","draft_reply","extract_facts","sales_signal"]'::jsonb,
  knowledge_scope JSONB NOT NULL DEFAULT '{}'::jsonb,   -- {profile_types:[...], include_untrusted:false}
  allowed_agent_spec_id TEXT,                      -- pin: phải set trước khi enable
  allowed_agent_spec_version TEXT,
  allowed_agent_spec_hash TEXT,
  eval_evidence_ref TEXT,                          -- ref eval evidence tươi; bắt buộc để enable
  eval_evidence_hash TEXT,                         -- hash spec mà evidence chứng nhận
  updated_by_workforce_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_engagement_copilot_settings_ws
  ON engagement.engagement_copilot_settings(workspace_id);

CREATE TABLE engagement.engagement_copilot_invocations (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  requested_by_workforce_member_id BIGINT NOT NULL,
  intent TEXT NOT NULL,
  run_id TEXT NOT NULL,
  agent_spec_id TEXT NOT NULL,
  agent_spec_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'dispatched',       -- dispatched | running | completed | failed | cancelled
  artifact_ref TEXT,                               -- ref artifact draft/summary khi completed
  summary_ref TEXT,
  identity_verified BOOLEAN NOT NULL DEFAULT false,
  feedback TEXT,                                   -- accepted | edited | rejected
  feedback_edited_ref TEXT,                        -- ref bản người sửa (nếu edited)
  feedback_by_workforce_member_id BIGINT,
  feedback_at TIMESTAMPTZ,
  correlation_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (thread_id, workspace_id)
    REFERENCES engagement.engagement_threads(id, workspace_id) ON DELETE CASCADE
);
CREATE INDEX idx_engagement_copilot_invocations_thread
  ON engagement.engagement_copilot_invocations(thread_id, created_at);
CREATE UNIQUE INDEX uq_engagement_copilot_invocations_run
  ON engagement.engagement_copilot_invocations(workspace_id, run_id);
