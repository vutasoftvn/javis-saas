-- 012_people_risk_dossier.up.sql
-- Founder-reviewed People Risk Dossier: bản ghi nghiệp vụ append-only, scoped
-- theo workspace + project. KHÔNG BAO GIỜ lưu CV, compensation, protected
-- characteristics, performance note, health data hay contact PII (email,
-- phone, tên gắn với chi tiết định danh) — chỉ lưu dữ liệu đã classify
-- (capacity_bands theo role-category/headcount, risk_signals theo category/
-- severity/sourceRef, source_refs theo pattern EvidenceRef của Product
-- Decision Dossier). Validation allowlist thực hiện ở service layer
-- (people-risk-dossier.service.ts); migration này chỉ định hình cột JSONB
-- generic để chứa các shape đã được validate đó. Xem CLAUDE.md quy tắc 1 &
-- 5, và task-1-brief §Global Constraints.

CREATE TABLE IF NOT EXISTS operating.people_risk_dossiers (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'DRAFT', -- DRAFT | CONFIRMED | SUPERSEDED
  current_version INT NOT NULL DEFAULT 1,
  created_by_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_people_risk_dossiers_proj_ws FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE,
  -- 1 dossier duy nhất mỗi Project (mirror uix_product_decision_dossiers_project
  -- ở migration 010 — cùng lý do: không có trạng thái nào hợp lệ hoá việc tồn
  -- tại dossier thứ hai cho cùng project).
  CONSTRAINT uix_people_risk_dossiers_project UNIQUE (workspace_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_people_risk_dossiers_proj
  ON operating.people_risk_dossiers (workspace_id, project_id, updated_at);

-- Append-only revision ledger. Không UPDATE/DELETE ở tầng ứng dụng — mỗi
-- revision mới link `supersedes_revision_id` về bản liền trước, CAS qua
-- `version` (khớp people_risk_dossiers.current_version tại thời điểm ghi).
CREATE TABLE IF NOT EXISTS operating.people_risk_dossier_revisions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  dossier_id BIGINT NOT NULL REFERENCES operating.people_risk_dossiers(id) ON DELETE CASCADE,
  version INT NOT NULL,
  status VARCHAR(24) NOT NULL, -- DRAFT | CONFIRMED
  -- Aggregate, no-name headcount/role-category counts. KHÔNG chứa tên người.
  capacity_bands JSONB NOT NULL DEFAULT '[]'::jsonb,
  -- Categorized risk labels (vd. single_point_of_failure, attrition_risk,
  -- hiring_gap) + severity + sourceRef — KHÔNG chứa raw text/performance note.
  risk_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
  -- Cùng shape EvidenceRef của Product Decision Dossier: sourceRef +
  -- classification + redacted excerpt, KHÔNG raw PII.
  source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  reason_code TEXT,
  narrative TEXT,
  actor_member_id BIGINT,
  confirmed_by_member_id BIGINT,
  confirmed_at TIMESTAMPTZ,
  supersedes_revision_id BIGINT REFERENCES operating.people_risk_dossier_revisions(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uix_people_risk_dossier_revisions_ver UNIQUE (dossier_id, version)
);

CREATE INDEX IF NOT EXISTS idx_people_risk_dossier_revisions_dossier
  ON operating.people_risk_dossier_revisions (dossier_id, created_at);
