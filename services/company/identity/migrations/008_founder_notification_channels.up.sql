-- 008_founder_notification_channels.up.sql
--
-- Task 2 (B1) / ADR-FOUNDER-CHANNEL-001: kênh nhận thông báo ngoài của founder
-- (Telegram trước, mở rộng `kind` sau qua service, không qua CHECK ở đây).
-- Dữ liệu profile của founder, không phải config tĩnh. Không lưu token thô —
-- `secret_ref` chỉ tham chiếu vault namespace `secret://cosa-connectors/`.
-- Mỗi (workspace_id, founder_member_id, kind) có tối đa một kênh chưa thu hồi.
-- Expand-only.

CREATE TABLE IF NOT EXISTS core.founder_notification_channels (
    id BIGINT PRIMARY KEY,
    workspace_id BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    founder_member_id BIGINT NOT NULL REFERENCES core.workforce_members(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    secret_ref TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    label TEXT,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_founder_notification_channels_active
    ON core.founder_notification_channels (workspace_id, founder_member_id, kind)
    WHERE revoked_at IS NULL;
