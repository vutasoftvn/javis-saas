-- 016_legal_issue_dossier.up.sql
-- Legal Issue Dossier: bản ghi NON-AUTHORITATIVE, append-only, scoped theo
-- workspace + project — chỉ ghi lại câu hỏi/vấn đề pháp lý đã được nêu ra và
-- THAM CHIẾU (không sao chép) các bản ghi legal thật đã tồn tại trong
-- `legal.legal_obligations` (finance-legal). Dossier này KHÔNG BAO GIỜ tạo/
-- sửa legal entity, ký/duyệt hợp đồng, đặt legal applicability, nộp hồ sơ/
-- liên hệ regulator, hay thuê luật sư — các service finance-legal hiện có
-- vẫn là nguồn sự thật duy nhất (task-1-brief §Global Constraints; CLAUDE.md
-- quy tắc 1). KHÔNG lưu nội dung hợp đồng đầy đủ, dữ liệu cá nhân hay tư vấn
-- privileged — chỉ lưu classification, source reference, jurisdiction/
-- applicability status và câu hỏi đã redact. Validation allowlist + deep
-- scan (contract-body-shaped / PII-shaped / privileged-advice-shaped) thực
-- hiện ở service layer (legal-issue-dossier.service.ts).

CREATE TABLE IF NOT EXISTS operating.legal_issue_dossiers (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'DRAFT', -- DRAFT | CONFIRMED | SUPERSEDED
  current_version INT NOT NULL DEFAULT 1,
  created_by_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_legal_issue_dossiers_proj_ws FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE,
  -- 1 dossier duy nhất mỗi Project (mirror uix_security_posture_dossiers_project
  -- ở migration 014 — cùng lý do: không có trạng thái nào hợp lệ hoá việc tồn
  -- tại dossier thứ hai cho cùng project).
  CONSTRAINT uix_legal_issue_dossiers_project UNIQUE (workspace_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_legal_issue_dossiers_proj
  ON operating.legal_issue_dossiers (workspace_id, project_id, updated_at);

-- Append-only revision ledger. Không UPDATE/DELETE ở tầng ứng dụng — mỗi
-- revision mới link `supersedes_revision_id` về bản liền trước, CAS qua
-- `version` (khớp legal_issue_dossiers.current_version tại thời điểm ghi).
CREATE TABLE IF NOT EXISTS operating.legal_issue_dossier_revisions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  dossier_id BIGINT NOT NULL REFERENCES operating.legal_issue_dossiers(id) ON DELETE CASCADE,
  version INT NOT NULL,
  status VARCHAR(24) NOT NULL, -- DRAFT | CONFIRMED
  -- Fixed enum, KHÔNG free text — phân loại vấn đề pháp lý đã nêu ra.
  issue_category VARCHAR(32) NOT NULL CHECK (issue_category IN (
    'CONTRACT_QUESTION', 'REGULATORY_QUESTION', 'IP_QUESTION',
    'EMPLOYMENT_QUESTION', 'DATA_PRIVACY_QUESTION', 'ENTITY_STRUCTURE_QUESTION',
    'DISPUTE_QUESTION', 'OTHER'
  )),
  -- Tham chiếu tới bản ghi legal THẬT (vd. obligation id) đã validate qua
  -- Finance-Legal read service (getObligationService) tại thời điểm ghi —
  -- KHÔNG sao chép nội dung bản ghi đó, chỉ lưu {recordType, recordId}.
  legal_record_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  -- Explicit fixed enum — KHÔNG BAO GIỜ null/undefined khi applicability
  -- không xác định được: dùng UNKNOWN/ESCALATED thay vì suy diễn (task-1-brief
  -- §Global Constraints: "missing applicability is an explicit unknown/
  -- escalation").
  applicability_status VARCHAR(24) NOT NULL DEFAULT 'UNKNOWN' CHECK (applicability_status IN (
    'APPLICABLE', 'NOT_APPLICABLE', 'UNKNOWN', 'ESCALATED'
  )),
  jurisdiction VARCHAR(64),
  -- Câu hỏi đã redact — KHÔNG chứa toàn văn hợp đồng, dữ liệu cá nhân, hay tư
  -- vấn privileged. Deep-scan ở service layer chặn shape giống các loại đó.
  redacted_question TEXT NOT NULL,
  reason_code VARCHAR(32) NOT NULL CHECK (reason_code IN (
    'ISSUE_RAISED', 'REFERENCE_UPDATED', 'APPLICABILITY_UPDATED',
    'ESCALATED', 'FOUNDER_REVIEW'
  )),
  actor_member_id BIGINT,
  confirmed_by_member_id BIGINT,
  confirmed_at TIMESTAMPTZ,
  supersedes_revision_id BIGINT REFERENCES operating.legal_issue_dossier_revisions(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uix_legal_issue_dossier_revisions_ver UNIQUE (dossier_id, version)
);

CREATE INDEX IF NOT EXISTS idx_legal_issue_dossier_revisions_dossier
  ON operating.legal_issue_dossier_revisions (dossier_id, created_at);
