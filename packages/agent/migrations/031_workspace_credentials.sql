-- Migration 031: Encrypted local credentials cho model routing (Task 2 —
-- plan 2026-09-07-local-first-model-routing). `models.model_provider_profiles`
-- (migration 030) chỉ lưu `credential_ref` (ID/reference) — bảng này là nơi
-- credential thật được lưu, LUÔN ở dạng ciphertext (AES-256-GCM, nonce
-- prepend, mã hoá bởi key cục bộ COSA_LOCAL_SECRETS_KEY_FILE — xem
-- apps/cosa/models/credential_store.py). KHÔNG BAO GIỜ có cột plaintext.
--
-- Bảng riêng (không nhét cột ciphertext vào model_provider_profiles) vì:
-- vòng đời credential (tạo/rotate/thu hồi) độc lập với vòng đời route
-- profile, và nhiều profile có thể tham chiếu cùng 1 credential_ref (vd 2
-- agent override cùng dùng 1 Anthropic API key) — 1-credential-nhiều-profile
-- sẽ gãy nếu ciphertext nằm trên chính hàng profile.
--
-- RLS fail-closed cùng convention với migration 026/029/030: không có
-- nhánh bypass, workspace_id phải được set_config('cosa.workspace_id', ...)
-- mỗi transaction; FORCE ROW LEVEL SECURITY áp dụng cả cho owner bảng.

CREATE TABLE IF NOT EXISTS models.workspace_credentials (
    workspace_id TEXT NOT NULL,
    credential_id TEXT NOT NULL,
    -- base64(nonce(12 byte) || AES-256-GCM ciphertext). AAD = workspace_id.
    ciphertext TEXT NOT NULL,
    key_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (workspace_id, credential_id)
);

CREATE INDEX IF NOT EXISTS idx_workspace_credentials_workspace
    ON models.workspace_credentials (workspace_id);

ALTER TABLE models.workspace_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE models.workspace_credentials FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS workspace_credentials_workspace_isolation ON models.workspace_credentials;
CREATE POLICY workspace_credentials_workspace_isolation ON models.workspace_credentials
    FOR ALL
    USING (workspace_id = current_setting('cosa.workspace_id', true))
    WITH CHECK (workspace_id = current_setting('cosa.workspace_id', true));
