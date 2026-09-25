-- 009_invitation_membership_grants.up.sql
-- Spec 2026-09-25 §8 — saga cấp membership ở core khi accept invitation.
-- Ghi ý định (requested) TRƯỚC khi gọi core, rồi core_granted → projected ở
-- các transaction cục bộ riêng; reconciler xử lý các bản ghi còn dở. Không
-- mô tả việc xuyên service là một transaction ACID. Expand-only.
CREATE TABLE IF NOT EXISTS cosa.organization_invitation_grants (
  id BIGINT PRIMARY KEY,
  invitation_id BIGINT NOT NULL UNIQUE REFERENCES cosa.organization_invitations(id) ON DELETE CASCADE,
  organization_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  requested_role TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'requested'
    CHECK (state IN ('requested', 'core_granted', 'projected', 'failed')),
  core_role TEXT,
  core_membership_version BIGINT,
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error_code TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_organization_invitation_grants_open
  ON cosa.organization_invitation_grants (state, updated_at)
  WHERE state IN ('requested', 'core_granted');
