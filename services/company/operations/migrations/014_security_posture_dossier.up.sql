-- 014_security_posture_dossier.up.sql
-- Founder-reviewed Security Posture Dossier: bản ghi nghiệp vụ append-only,
-- scoped theo workspace + project. KHÔNG BAO GIỜ lưu password, token, API
-- key, private key, full request header, raw vulnerability payload hay
-- infrastructure topology — chỉ lưu dữ liệu đã classify (controls theo
-- category/state, findings theo severity/category/sourceRef, evidence_refs
-- theo pattern EvidenceRef của Product Decision Dossier). Validation
-- allowlist + deep secret-pattern scan thực hiện ở service layer
-- (security-posture.service.ts); migration này chỉ định hình cột JSONB
-- generic để chứa các shape đã được validate đó. Xem CLAUDE.md quy tắc 1 &
-- 5, và task-1-brief §Global Constraints ("Reject passwords, tokens, private
-- keys, full request headers, raw vulnerability payloads and infrastructure
-- topology from all dossier inputs/logs").

CREATE TABLE IF NOT EXISTS operating.security_posture_dossiers (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'DRAFT', -- DRAFT | CONFIRMED | SUPERSEDED
  current_version INT NOT NULL DEFAULT 1,
  created_by_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_security_posture_dossiers_proj_ws FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE,
  -- 1 dossier duy nhất mỗi Project (mirror uix_people_risk_dossiers_project
  -- ở migration 012 — cùng lý do: không có trạng thái nào hợp lệ hoá việc
  -- tồn tại dossier thứ hai cho cùng project).
  CONSTRAINT uix_security_posture_dossiers_project UNIQUE (workspace_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_security_posture_dossiers_proj
  ON operating.security_posture_dossiers (workspace_id, project_id, updated_at);

-- Append-only revision ledger. Không UPDATE/DELETE ở tầng ứng dụng — mỗi
-- revision mới link `supersedes_revision_id` về bản liền trước, CAS qua
-- `version` (khớp security_posture_dossiers.current_version tại thời điểm
-- ghi).
CREATE TABLE IF NOT EXISTS operating.security_posture_dossier_revisions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  dossier_id BIGINT NOT NULL REFERENCES operating.security_posture_dossiers(id) ON DELETE CASCADE,
  version INT NOT NULL,
  status VARCHAR(24) NOT NULL, -- DRAFT | CONFIRMED
  -- Classified control states (controlId/category/state cố định) — KHÔNG
  -- chứa raw config/credential text.
  controls JSONB NOT NULL DEFAULT '[]'::jsonb,
  -- Classified findings (severity/category cố định + sourceRef) — KHÔNG
  -- chứa raw vulnerability payload.
  findings JSONB NOT NULL DEFAULT '[]'::jsonb,
  -- Cùng shape EvidenceRef của Product Decision Dossier: sourceRef +
  -- classification + redacted excerpt, KHÔNG raw secret/topology.
  evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  -- Aggregate severity của revision (max trong findings tại thời điểm ghi).
  severity VARCHAR(16) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
  -- Fixed enum, KHÔNG free text — không có trường narrative/free-text nào
  -- trên write path của dossier này (mirror finding Critical đã sửa ở People
  -- Risk Dossier: một trường narrative tự do sẽ đánh bại headline
  -- secret-free property, vì secret không có "shape" cố định để quét hết).
  reason_code VARCHAR(32) NOT NULL CHECK (reason_code IN (
    'INITIAL_ASSESSMENT', 'CONTROL_UPDATED', 'FINDING_ADDED',
    'EVIDENCE_UPDATED', 'FOUNDER_REVIEW'
  )),
  actor_member_id BIGINT,
  confirmed_by_member_id BIGINT,
  confirmed_at TIMESTAMPTZ,
  supersedes_revision_id BIGINT REFERENCES operating.security_posture_dossier_revisions(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uix_security_posture_dossier_revisions_ver UNIQUE (dossier_id, version)
);

CREATE INDEX IF NOT EXISTS idx_security_posture_dossier_revisions_dossier
  ON operating.security_posture_dossier_revisions (dossier_id, created_at);
