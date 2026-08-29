-- services/company/identity/migrations/4_workspace_slugs.up.sql
-- M2 §6 / ADR-SLUG-001 — bảng giữ chỗ slug. Unique-while-active là cơ chế
-- reservation atomic. workspace_id KHÔNG đổi khi rename (tạo row REDIRECT).
CREATE TABLE IF NOT EXISTS core.workspace_slugs (
  id                BIGINT PRIMARY KEY,
  workspace_id      BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
  slug              TEXT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'ACTIVE'
                      CHECK (status IN ('ACTIVE', 'REDIRECT', 'RELEASED')),
  redirect_to_slug  TEXT,
  reserved_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  released_at       TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_workspace_slugs_active
  ON core.workspace_slugs (slug) WHERE status IN ('ACTIVE', 'REDIRECT');

CREATE INDEX IF NOT EXISTS idx_workspace_slugs_workspace
  ON core.workspace_slugs (workspace_id);

-- Một workspace có tối đa một slug ACTIVE tại một thời điểm.
CREATE UNIQUE INDEX IF NOT EXISTS uq_workspace_slugs_one_active_per_workspace
  ON core.workspace_slugs (workspace_id) WHERE status = 'ACTIVE';
