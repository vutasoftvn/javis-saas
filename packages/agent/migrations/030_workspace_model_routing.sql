-- Migration 030: Local-first model routing — persist per-workspace model
-- provider profiles và policy (default/override/fallback), thay thế thế
-- giới "1 DeepSeek model global đọc thẳng từ DEEPSEEK_* env" hiện tại
-- (apps/cosa/composition/model_provider.py::build_deepseek_model()).
--
-- Task 1 (plan 2026-09-07-local-first-model-routing) — CHỈ tạo schema +
-- typed contracts/repository/resolver; KHÔNG wire vào model_provider.py hay
-- kernel (task sau). `credential_ref` chỉ là ID/reference tới secret lưu ở
-- nơi khác (Task 2) — bảng này KHÔNG BAO GIỜ lưu giá trị secret/API key thô.
--
-- RLS viết theo dạng fail-closed thật (cùng convention với migration
-- 026/029: KHÔNG có nhánh bypass "OR current_setting(...) IS NULL" — một
-- transaction quên set_config('cosa.workspace_id', ...) sẽ không đọc được
-- gì, không phải đọc được toàn bộ) + FORCE ROW LEVEL SECURITY (chủ sở hữu
-- bảng agent_migrator cũng không tự động bypass).

CREATE SCHEMA IF NOT EXISTS models;

-- ── models.model_provider_profiles — 1 route model cụ thể, thuộc đúng 1 workspace ──

CREATE TABLE IF NOT EXISTS models.model_provider_profiles (
    workspace_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    provider_type TEXT NOT NULL CHECK (
        provider_type IN (
            'local_openai_compatible', 'anthropic_api', 'openai_api',
            'openrouter_api', 'deepseek_api', 'claude_cli', 'codex_cli',
            'gemini_cli'
        )
    ),
    model_id TEXT NOT NULL,
    -- Chỉ ID/reference tới credential lưu nơi khác (Task 2) — không phải secret thô.
    credential_ref TEXT,
    allowed_models JSONB NOT NULL DEFAULT '[]'::jsonb,
    budget_usd_limit NUMERIC,
    max_concurrency INTEGER CHECK (max_concurrency IS NULL OR max_concurrency > 0),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'DISABLED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, profile_id)
);

CREATE INDEX IF NOT EXISTS idx_model_provider_profiles_workspace_status
    ON models.model_provider_profiles (workspace_id, status);

-- ── models.workspace_model_policies — default (WORKSPACE) / override (AGENT_PROFILE) ──
-- Fallback CHỈ là allowlist tường minh trên chính policy — không có fallback
-- ngầm định nào khác trong resolver.

CREATE TABLE IF NOT EXISTS models.workspace_model_policies (
    workspace_id TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('WORKSPACE', 'AGENT_PROFILE')),
    -- scope='WORKSPACE'      => scope_key = workspace_id
    -- scope='AGENT_PROFILE'  => scope_key = agent_spec_id (vd. "cosa.agents.operations")
    scope_key TEXT NOT NULL,
    primary_profile_id TEXT NOT NULL,
    fallback_profile_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, scope, scope_key),
    FOREIGN KEY (workspace_id, primary_profile_id)
        REFERENCES models.model_provider_profiles (workspace_id, profile_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_workspace_model_policies_workspace_scope
    ON models.workspace_model_policies (workspace_id, scope);

-- ── RLS fail-closed ──

ALTER TABLE models.model_provider_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE models.model_provider_profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE models.workspace_model_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE models.workspace_model_policies FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS model_provider_profiles_workspace_isolation ON models.model_provider_profiles;
CREATE POLICY model_provider_profiles_workspace_isolation ON models.model_provider_profiles
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));

DROP POLICY IF EXISTS workspace_model_policies_workspace_isolation ON models.workspace_model_policies;
CREATE POLICY workspace_model_policies_workspace_isolation ON models.workspace_model_policies
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));
