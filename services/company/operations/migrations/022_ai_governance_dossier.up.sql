-- 022_ai_governance_dossier.up.sql
-- AI Governance Dossier (Task 2, CAIO plan): bản ghi REFERENCE-ONLY, append-
-- only, scoped theo workspace + project — chỉ ghi lại tham chiếu tới 1
-- snapshot đã ký bởi services/cosa
-- (services/cosa/services/ai-governance-snapshot.service.ts): policy/
-- evaluator id+version+definitionHash, status, observedAt, và 1 hash tham
-- chiếu độc lập của snapshot (snapshot_ref) — KHÔNG BAO GIỜ raw signature,
-- prompt transcript, API key, provider credential, raw user message, model
-- output hay vulnerability payload (task-2-brief §Global Constraints). Deep-
-- scan chặn các shape đó ở service layer (ai-governance-dossier.service.ts)
-- trước khi bất kỳ giá trị nào chạm bảng này; migration này chỉ mô tả cấu
-- trúc lưu trữ đã validate. Founder xác nhận qua CONFIRMED status — agent
-- context không bao giờ ghi được (chỉ đọc).

CREATE TABLE IF NOT EXISTS operating.ai_governance_dossiers (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'DRAFT', -- DRAFT | CONFIRMED | SUPERSEDED
  current_version INT NOT NULL DEFAULT 1,
  created_by_member_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_ai_governance_dossiers_proj_ws FOREIGN KEY (project_id, workspace_id)
    REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE,
  -- 1 dossier duy nhất mỗi Project (mirror uix_data_governance_dossiers_project
  -- ở migration 019 — cùng lý do: không có trạng thái nào hợp lệ hoá việc tồn
  -- tại dossier thứ hai cho cùng project).
  CONSTRAINT uix_ai_governance_dossiers_project UNIQUE (workspace_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_ai_governance_dossiers_proj
  ON operating.ai_governance_dossiers (workspace_id, project_id, updated_at);

-- Append-only revision ledger. Không UPDATE/DELETE ở tầng ứng dụng — mỗi
-- revision mới link `supersedes_revision_id` về bản liền trước, CAS qua
-- `version` (khớp ai_governance_dossiers.current_version tại thời điểm ghi).
CREATE TABLE IF NOT EXISTS operating.ai_governance_dossier_revisions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  dossier_id BIGINT NOT NULL REFERENCES operating.ai_governance_dossiers(id) ON DELETE CASCADE,
  version INT NOT NULL,
  status VARCHAR(24) NOT NULL, -- DRAFT | CONFIRMED
  -- Hash tham chiếu độc lập của snapshot đã verify (KHÔNG phải raw signature
  -- — xem computeSnapshotRef trong service layer).
  snapshot_ref VARCHAR(128) NOT NULL,
  -- Mảng {id, version, definitionHash} — id/version/hash CANONICAL của
  -- policy/evaluator, đã verify signature trước khi ghi. KHÔNG BAO GIỜ chứa
  -- nội dung policy/eval thật, chỉ danh tính tham chiếu.
  policy JSONB NOT NULL DEFAULT '[]'::jsonb,
  evaluators JSONB NOT NULL DEFAULT '[]'::jsonb,
  -- Thời điểm services/cosa quan sát/ký snapshot (từ envelope đã verify).
  observed_at TIMESTAMPTZ NOT NULL,
  -- Mảng {category, severity} — enum cố định, không có field tự do.
  risk_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
  -- Tham chiếu nguồn đã redact (reference-only shape, mirror EvidenceRef của
  -- các dossier khác) — KHÔNG BAO GIỜ raw file URI/path hay credential.
  source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
  reason_code VARCHAR(32) NOT NULL CHECK (reason_code IN (
    'SNAPSHOT_INGESTED', 'RISK_SIGNAL_UPDATED', 'SOURCE_REF_UPDATED', 'FOUNDER_REVIEW'
  )),
  actor_member_id BIGINT,
  confirmed_by_member_id BIGINT,
  confirmed_at TIMESTAMPTZ,
  supersedes_revision_id BIGINT REFERENCES operating.ai_governance_dossier_revisions(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uix_ai_governance_dossier_revisions_ver UNIQUE (dossier_id, version)
);

CREATE INDEX IF NOT EXISTS idx_ai_governance_dossier_revisions_dossier
  ON operating.ai_governance_dossier_revisions (dossier_id, created_at);
