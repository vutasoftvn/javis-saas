-- 010_product_decision_dossier.up.sql
-- Founder-reviewed Product Decision Dossier: bản ghi nghiệp vụ append-only,
-- scoped theo workspace + project. Model/agent context KHÔNG BAO GIỜ được
-- phép ghi bảng này trực tiếp (guard ở service layer) — chỉ đọc snapshot đã
-- redact. Xem CLAUDE.md quy tắc 1: business truth thuộc services/*.

CREATE TABLE IF NOT EXISTS operating.product_decision_dossiers (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  title VARCHAR(255) NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'DRAFT', -- DRAFT | CONFIRMED | SUPERSEDED
  current_version INT NOT NULL DEFAULT 1,
  created_by_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_product_decision_dossiers_proj_ws FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_product_decision_dossiers_proj
  ON operating.product_decision_dossiers (workspace_id, project_id, updated_at);

-- Append-only revision ledger. Không UPDATE/DELETE ở tầng ứng dụng — mỗi
-- revision mới link `supersedes_revision_id` về bản liền trước, CAS qua
-- `version` (khớp product_decision_dossiers.current_version tại thời điểm ghi).
CREATE TABLE IF NOT EXISTS operating.product_decision_dossier_revisions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  dossier_id BIGINT NOT NULL REFERENCES operating.product_decision_dossiers(id) ON DELETE CASCADE,
  version INT NOT NULL,
  status VARCHAR(24) NOT NULL, -- DRAFT | CONFIRMED
  assumptions JSONB NOT NULL DEFAULT '[]'::jsonb,
  evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb, -- chỉ source ref + classification + redacted excerpt, KHÔNG raw PII
  reason_code TEXT,
  narrative TEXT,
  actor_member_id BIGINT,
  confirmed_by_member_id BIGINT,
  confirmed_at TIMESTAMPTZ,
  supersedes_revision_id BIGINT REFERENCES operating.product_decision_dossier_revisions(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uix_product_decision_dossier_revisions_ver UNIQUE (dossier_id, version)
);

CREATE INDEX IF NOT EXISTS idx_product_decision_dossier_revisions_dossier
  ON operating.product_decision_dossier_revisions (dossier_id, created_at);
