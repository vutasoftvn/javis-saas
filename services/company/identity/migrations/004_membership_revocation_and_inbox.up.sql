-- Migration 004: Membership revocation state and inbox for Core propagation
ALTER TABLE core.workspace_memberships
  ADD COLUMN IF NOT EXISTS membership_state TEXT NOT NULL DEFAULT 'active',
  ADD COLUMN IF NOT EXISTS source_membership_version BIGINT NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS core.membership_event_inbox (
  event_id TEXT PRIMARY KEY,
  organization_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  membership_version BIGINT NOT NULL,
  status TEXT NOT NULL,
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workspace_memberships_state_version
  ON core.workspace_memberships (workspace_id, user_id, membership_state, source_membership_version);
