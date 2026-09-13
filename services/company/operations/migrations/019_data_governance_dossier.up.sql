-- 019_data_governance_dossier.up.sql
-- Data Governance Dossier: bản ghi METADATA-ONLY, append-only, scoped theo
-- workspace + project — chỉ ghi lại catalog entry của data asset (asset
-- reference, classification, quality status) và tham chiếu nguồn (sourceRefs)
-- đã redact. Dossier này KHÔNG BAO GIỜ lưu giá trị/field sample thật, embedding
-- vector, raw file URI/path hay API credential — deep-scan chặn các shape đó
-- ở service layer (data-governance-dossier.service.ts), migration này chỉ mô
-- tả cấu trúc lưu trữ đã được validate trước khi tới đây (task-1-brief
-- §Global Constraints: "deny values, field samples, embeddings, raw file URI,
-- API credentials and cross-Project lineage"). CDO không tự mutate ACL hay
-- xoá bản ghi — chỉ founder data steward xác nhận qua CONFIRMED status.

CREATE TABLE IF NOT EXISTS operating.data_governance_dossiers (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'DRAFT', -- DRAFT | CONFIRMED | SUPERSEDED
  current_version INT NOT NULL DEFAULT 1,
  created_by_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_data_governance_dossiers_proj_ws FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE,
  -- 1 dossier duy nhất mỗi Project (mirror uix_legal_issue_dossiers_project ở
  -- migration 016 — cùng lý do: không có trạng thái nào hợp lệ hoá việc tồn
  -- tại dossier thứ hai cho cùng project).
  CONSTRAINT uix_data_governance_dossiers_project UNIQUE (workspace_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_data_governance_dossiers_proj
  ON operating.data_governance_dossiers (workspace_id, project_id, updated_at);

-- Append-only revision ledger. Không UPDATE/DELETE ở tầng ứng dụng — mỗi
-- revision mới link `supersedes_revision_id` về bản liền trước, CAS qua
-- `version` (khớp data_governance_dossiers.current_version tại thời điểm ghi).
CREATE TABLE IF NOT EXISTS operating.data_governance_dossier_revisions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  dossier_id BIGINT NOT NULL REFERENCES operating.data_governance_dossiers(id) ON DELETE CASCADE,
  version INT NOT NULL,
  status VARCHAR(24) NOT NULL, -- DRAFT | CONFIRMED
  -- Mảng {assetId, classification, qualityStatus} — mỗi phần tử validate qua
  -- allowlist nghiêm ngặt + enum cố định ở service layer. KHÔNG BAO GIỜ chứa
  -- field sample/giá trị dữ liệu thật, chỉ opaque reference + nhãn phân loại.
  assets JSONB NOT NULL DEFAULT '[]'::jsonb,
  -- Tham chiếu nguồn đã redact (reference-only shape, mirror EvidenceRef của
  -- các dossier khác) — KHÔNG BAO GIỜ raw file URI/path hay credential.
  source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  reason_code VARCHAR(32) NOT NULL CHECK (reason_code IN (
    'ASSET_CATALOGED', 'CLASSIFICATION_UPDATED', 'QUALITY_UPDATED',
    'SOURCE_REF_UPDATED', 'FOUNDER_REVIEW'
  )),
  actor_member_id BIGINT,
  confirmed_by_member_id BIGINT,
  confirmed_at TIMESTAMPTZ,
  supersedes_revision_id BIGINT REFERENCES operating.data_governance_dossier_revisions(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uix_data_governance_dossier_revisions_ver UNIQUE (dossier_id, version)
);

CREATE INDEX IF NOT EXISTS idx_data_governance_dossier_revisions_dossier
  ON operating.data_governance_dossier_revisions (dossier_id, created_at);
