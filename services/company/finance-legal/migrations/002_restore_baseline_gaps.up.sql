-- SP-A: restore the legal schema structure the 001 baseline squash dropped.
-- Bản squash baseline Founder Trial R1 (commit 81461673, `pg_dump --schema-only`)
-- gộp toàn bộ lịch sử migration finance-legal thành một file 001 và trong quá
-- trình đó KHÔNG tạo bảng legal.* nào. Runtime AI-compliance
-- (ai-compliance-access / ai-compliance-snapshot / ai-legal-applicability
-- services — nằm trên đường `resolve-data-use` gate mọi agent run) và 18 suite
-- vitest finance-legal cần các bảng này.
--
-- File này flatten phần DDL cấu trúc từ các migration đã bị xoá ở git ref
-- 81461673^:
--   - 12_legal_catalog                     (regulation catalog)
--   - 13_legal_applicability_obligations    (entity profiles, obligation templates/instances)
--   - 27_ai_compliance_governance           (13 bảng AI-compliance governance)
--   - 29_ai_compliance_runtime_hardening    (composite UNIQUE/FK + snapshot provenance columns)
--   - 30_ai_legal_source_corrections        (regulation_versions/evidence columns + ai_applicability_rules)
--   - 31_ai_legal_review_pending_correction (regulation_versions.legal_review_confirmed)
--
-- Ngoài 6 migration trên, 3 bảng dưới đây có trong
-- services/company/shared/db/schema/legal.ts nhưng nằm ở migration ngoài phạm vi
-- (23/32/34) — vẫn tạo lại ở đây để schema `legal` khớp đủ 23 export của
-- legal.ts (theo approach guidance của task brief):
--   - legal_verification_approvals  (từ 23_legal_verification_approvals)
--   - applicability_evaluations      (từ 32_legal_predicate_versions)
--   - obligation_transitions         (từ 34_obligation_lifecycle)
-- Và các cột do migration 33/34 thêm vào bảng đã có (workspace_ai_deployments,
-- legal_obligation_instances) cũng được thêm lại để khớp legal.ts.
--
-- CHỈ cấu trúc — KHÔNG seed nội dung regulation/rule (không INSERT/UPDATE/DELETE):
-- phần seed được cố ý hoãn sang task sau. Expand-only, idempotent (chạy lại
-- nhiều lần không lỗi): mọi CREATE TABLE/INDEX dùng IF NOT EXISTS, mọi
-- ADD CONSTRAINT bọc trong khối DO ... EXCEPTION WHEN duplicate_object.
--
-- Deviation duy nhất so với nguyên văn migration nguồn: bảng
-- legal.legal_entity_profiles KHÔNG có cột platform_company_id và KHÔNG có CHECK
-- trên cột status — cả hai đã bị 25_legal_entity_status_v2 (ngoài phạm vi) đổi;
-- legal.ts không model chúng nên theo quy tắc "Drizzle thắng khi bất đồng" ta
-- theo legal.ts.

CREATE SCHEMA IF NOT EXISTS legal;

-- =========================================================================
-- from 12_legal_catalog.up.sql — regulation sources & versions catalog
-- =========================================================================
CREATE TABLE IF NOT EXISTS legal.regulation_sources (
  id           BIGINT PRIMARY KEY,
  source_name  TEXT NOT NULL,
  issuer       TEXT NOT NULL,
  number       TEXT NOT NULL UNIQUE,
  url          TEXT NOT NULL,
  content_hash TEXT,
  layer        TEXT NOT NULL CHECK (layer IN ('CURRENT_LAW','POLICY_WATCH','PROFESSIONAL_REVIEW')),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS legal.regulation_versions (
  id                    BIGINT PRIMARY KEY,
  regulation_source_id  BIGINT NOT NULL REFERENCES legal.regulation_sources(id) ON DELETE CASCADE,
  version               TEXT NOT NULL,
  effective_from        DATE NOT NULL,
  effective_to          DATE,
  superseded_by_id      BIGINT REFERENCES legal.regulation_versions(id) ON DELETE SET NULL,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (regulation_source_id, version)
);

CREATE INDEX IF NOT EXISTS idx_regulation_versions_source_effective
  ON legal.regulation_versions(regulation_source_id, effective_from);

-- from 30_ai_legal_source_corrections.up.sql §1 — cột thẩm định + provenance
ALTER TABLE legal.regulation_versions
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'ACTIVE',
  ADD COLUMN IF NOT EXISTS content_hash text,
  ADD COLUMN IF NOT EXISTS correction_reason text,
  ADD COLUMN IF NOT EXISTS artifact_path text,
  ADD COLUMN IF NOT EXISTS reviewer_member_id bigint,
  ADD COLUMN IF NOT EXISTS reviewed_at timestamp with time zone;

-- from 31_ai_legal_review_pending_correction.up.sql §1 — cờ xác nhận review pháp lý THẬT
ALTER TABLE legal.regulation_versions
  ADD COLUMN IF NOT EXISTS legal_review_confirmed boolean NOT NULL DEFAULT false;

-- =========================================================================
-- from 13_legal_applicability_obligations.up.sql — entity profiles, obligation
-- templates/instances, applicability rules
-- =========================================================================
-- Lưu ý: bỏ cột platform_company_id và CHECK trên status (25_legal_entity_status_v2
-- ngoài phạm vi đã đổi enum sang DRAFT|REGISTRATION_PREPARATION|
-- REGISTERED_UNVERIFIED|VERIFIED|SUSPENDED|DISSOLVED và drop platform_company_id).
-- legal.ts model status là `text NOT NULL DEFAULT 'DRAFT'` không CHECK — theo đó.
CREATE TABLE IF NOT EXISTS legal.legal_entity_profiles (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL,
  entity_type           TEXT NOT NULL,
  status                TEXT NOT NULL DEFAULT 'DRAFT',
  registration_number   TEXT,
  tax_id                TEXT,
  verified_by_member_id BIGINT,
  verified_at           TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_legal_entity_profiles_workspace
  ON legal.legal_entity_profiles(workspace_id);

-- from 23_legal_verification_approvals.up.sql — durable approval record cho legal
-- verification (bind workspace + entity + expected_status, expiry + separation-of-duty)
CREATE TABLE IF NOT EXISTS legal.legal_verification_approvals (
  id               BIGINT PRIMARY KEY,
  workspace_id     BIGINT NOT NULL,
  legal_entity_id  BIGINT NOT NULL REFERENCES legal.legal_entity_profiles(id) ON DELETE CASCADE,
  expected_status  TEXT NOT NULL,
  requested_by     BIGINT NOT NULL,
  approved_by      BIGINT,
  status           TEXT NOT NULL DEFAULT 'PENDING'
                     CHECK (status IN ('PENDING','APPROVED','REJECTED','EXPIRED')),
  requested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  decided_at       TIMESTAMPTZ,
  expires_at       TIMESTAMPTZ NOT NULL,
  rationale        TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_legal_verification_approvals_pending
  ON legal.legal_verification_approvals (workspace_id, legal_entity_id, expected_status)
  WHERE status = 'PENDING';
CREATE INDEX IF NOT EXISTS idx_legal_verification_approvals_ws_entity
  ON legal.legal_verification_approvals (workspace_id, legal_entity_id);

CREATE TABLE IF NOT EXISTS legal.legal_obligation_templates (
  id                       BIGINT PRIMARY KEY,
  regulation_version_id    BIGINT NOT NULL REFERENCES legal.regulation_versions(id) ON DELETE CASCADE,
  title                    TEXT NOT NULL,
  description              TEXT,
  typical_due_offset_days  INTEGER,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS legal.applicability_rules (
  id                       BIGINT PRIMARY KEY,
  regulation_version_id    BIGINT NOT NULL REFERENCES legal.regulation_versions(id) ON DELETE CASCADE,
  predicate                JSONB NOT NULL,
  obligation_template_id   BIGINT NOT NULL REFERENCES legal.legal_obligation_templates(id) ON DELETE CASCADE,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- from 32_legal_predicate_versions.up.sql — persisted applicability evaluations
CREATE TABLE IF NOT EXISTS legal.applicability_evaluations (
  id               BIGINT PRIMARY KEY,
  workspace_id     BIGINT NOT NULL,
  legal_entity_id  BIGINT NOT NULL,
  rule_id          BIGINT NOT NULL,
  rule_version     TEXT NOT NULL DEFAULT '1.0',
  facts_version    TEXT NOT NULL DEFAULT '1.0',
  result           TEXT NOT NULL,
  reason_codes     JSONB NOT NULL DEFAULT '[]'::jsonb,
  evaluated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_ref       TEXT,
  CONSTRAINT uq_entity_rule_facts_version UNIQUE (legal_entity_id, rule_id, facts_version)
);
CREATE INDEX IF NOT EXISTS idx_applicability_eval_ws_entity
  ON legal.applicability_evaluations(workspace_id, legal_entity_id);

CREATE TABLE IF NOT EXISTS legal.legal_obligation_instances (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  legal_entity_profile_id    BIGINT REFERENCES legal.legal_entity_profiles(id) ON DELETE SET NULL,
  template_id                BIGINT REFERENCES legal.legal_obligation_templates(id) ON DELETE SET NULL,
  regulation_version_id      BIGINT REFERENCES legal.regulation_versions(id) ON DELETE SET NULL,
  source                     TEXT NOT NULL CHECK (source IN ('REGULATION_TEMPLATE','USER_CREATED','AI_PROPOSAL')),
  title                      TEXT NOT NULL,
  due_date                   DATE,
  status                     TEXT NOT NULL DEFAULT 'OPEN',
  evidence_artifact_id       BIGINT,
  applicability_assessed_at  TIMESTAMPTZ,
  owner_member_id            BIGINT,
  review_status              TEXT NOT NULL DEFAULT 'PENDING',
  legacy_ref                 TEXT UNIQUE,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_legal_obligation_instances_workspace_status
  ON legal.legal_obligation_instances(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_legal_obligation_instances_workspace_due
  ON legal.legal_obligation_instances(workspace_id, due_date);

-- from 34_obligation_lifecycle.up.sql — cột lifecycle + idempotency index +
-- bảng audit trail chuyển trạng thái obligation
ALTER TABLE legal.legal_obligation_instances
  ADD COLUMN IF NOT EXISTS period_key TEXT,
  ADD COLUMN IF NOT EXISTS evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS uq_legal_obligation_period_entity
  ON legal.legal_obligation_instances (workspace_id, template_id, period_key, COALESCE(legal_entity_profile_id, 0))
  WHERE template_id IS NOT NULL AND period_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS legal.obligation_transitions (
  id                     BIGINT PRIMARY KEY,
  workspace_id           BIGINT NOT NULL,
  obligation_instance_id BIGINT NOT NULL REFERENCES legal.legal_obligation_instances(id) ON DELETE CASCADE,
  from_status            TEXT NOT NULL,
  to_status              TEXT NOT NULL,
  evidence_artifact_id   BIGINT,
  evidence_refs          JSONB NOT NULL DEFAULT '[]'::jsonb,
  actor_member_id        BIGINT,
  rationale              TEXT,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_obligation_transitions_instance
  ON legal.obligation_transitions (obligation_instance_id, created_at DESC);

-- =========================================================================
-- from 27_ai_compliance_governance.up.sql — AI compliance & governance
-- (13 bảng, reproduce nguyên văn — đã là CREATE TABLE IF NOT EXISTS)
-- =========================================================================
CREATE TABLE IF NOT EXISTS legal.ai_system_catalog (
  id                         BIGINT PRIMARY KEY,
  system_key                 TEXT NOT NULL UNIQUE,
  name                       TEXT NOT NULL,
  allowed_purposes           JSONB NOT NULL DEFAULT '[]'::jsonb,
  prohibited_purposes        JSONB NOT NULL DEFAULT '[]'::jsonb,
  technical_owner_member_id  BIGINT,
  lifecycle_status           TEXT NOT NULL DEFAULT 'DRAFT' CHECK (lifecycle_status IN ('DRAFT','ACTIVE','DEPRECATED','RETIRED')),
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS legal.ai_system_versions (
  id                         BIGINT PRIMARY KEY,
  system_catalog_id          BIGINT NOT NULL REFERENCES legal.ai_system_catalog(id) ON DELETE CASCADE,
  version                    TEXT NOT NULL,
  config_hash                TEXT NOT NULL,
  model_profile_ref          TEXT,
  status                     TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','ACTIVE','DEPRECATED','RETIRED')),
  released_at                TIMESTAMPTZ,
  deprecated_at              TIMESTAMPTZ,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (system_catalog_id, version)
);
CREATE INDEX IF NOT EXISTS idx_ai_system_versions_catalog
  ON legal.ai_system_versions (system_catalog_id);

CREATE TABLE IF NOT EXISTS legal.workspace_ai_deployments (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  system_version_id          BIGINT NOT NULL REFERENCES legal.ai_system_versions(id),
  mode                       TEXT NOT NULL CHECK (mode = 'ADVISORY_ONLY'),
  status                     TEXT NOT NULL CHECK (status IN ('DRAFT','ASSESSED','APPROVED_FOR_USE','SUSPENDED','REJECTED','RETIRED')),
  founder_member_id          BIGINT NOT NULL,
  technical_owner_member_id  BIGINT,
  current_assessment_id      BIGINT,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS workspace_ai_deployments_workspace_status_idx
  ON legal.workspace_ai_deployments (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_workspace_ai_deployments_workspace
  ON legal.workspace_ai_deployments (workspace_id);

-- from 33_deployment_authority_versions.up.sql — workforce authority + policy versioning
ALTER TABLE legal.workspace_ai_deployments
  ADD COLUMN IF NOT EXISTS created_by_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS accountable_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS reviewer_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS approved_by_member_id BIGINT,
  ADD COLUMN IF NOT EXISTS policy_version INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS approved_version INTEGER;

CREATE TABLE IF NOT EXISTS legal.ai_system_capability_bindings (
  id                         BIGINT PRIMARY KEY,
  system_version_id          BIGINT NOT NULL REFERENCES legal.ai_system_versions(id) ON DELETE CASCADE,
  capability_id              TEXT NOT NULL,
  effect_class               TEXT NOT NULL CHECK (effect_class IN ('READ','DRAFT','EXTERNAL')),
  decision_domain            TEXT NOT NULL CHECK (decision_domain IN ('GENERAL','LEGAL','FINANCE','HR','OPERATIONS','COMMERCIAL')),
  requires_human_confirmation BOOLEAN NOT NULL DEFAULT true,
  may_send_to_model          BOOLEAN NOT NULL DEFAULT false,
  max_data_category          TEXT NOT NULL CHECK (max_data_category IN ('NON_PERSONAL','PERSONAL','SENSITIVE_PERSONAL','BUSINESS_CONFIDENTIAL')),
  action_recipient_scope     TEXT,
  prohibited_purpose         BOOLEAN NOT NULL DEFAULT false,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (system_version_id, capability_id)
);
CREATE INDEX IF NOT EXISTS idx_ai_capability_bindings_version
  ON legal.ai_system_capability_bindings (system_version_id);

CREATE TABLE IF NOT EXISTS legal.ai_risk_assessments (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  deployment_id              BIGINT NOT NULL REFERENCES legal.workspace_ai_deployments(id) ON DELETE CASCADE,
  classification             TEXT NOT NULL CHECK (classification IN ('OUT_OF_CATALOG','REQUIRES_REVIEW','HIGH_RISK')),
  intended_purpose           TEXT NOT NULL,
  affected_stakeholders      JSONB NOT NULL DEFAULT '[]'::jsonb,
  controls                   JSONB NOT NULL DEFAULT '[]'::jsonb,
  reviewer_member_id         BIGINT,
  approved_by_member_id      BIGINT,
  approved_at                TIMESTAMPTZ,
  rationale                  TEXT,
  expires_at                 TIMESTAMPTZ NOT NULL,
  status                     TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','APPROVED','REJECTED','EXPIRED')),
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_risk_assessments_workspace_deployment_idx
  ON legal.ai_risk_assessments (workspace_id, deployment_id);
CREATE INDEX IF NOT EXISTS idx_ai_risk_assessments_workspace
  ON legal.ai_risk_assessments (workspace_id);

-- deferred single-column FK (27_ai_compliance_governance): workspace_ai_deployments
-- .current_assessment_id -> ai_risk_assessments(id); thêm sau khi cả hai bảng tồn tại.
DO $$ BEGIN
  ALTER TABLE legal.workspace_ai_deployments
    ADD CONSTRAINT fk_workspace_ai_deployments_assessment
    FOREIGN KEY (current_assessment_id)
    REFERENCES legal.ai_risk_assessments(id)
    ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS legal.ai_compliance_evidence (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  assessment_id              BIGINT NOT NULL REFERENCES legal.ai_risk_assessments(id) ON DELETE CASCADE,
  evidence_type              TEXT NOT NULL,
  uri_reference              TEXT NOT NULL,
  content_hash               TEXT NOT NULL,
  checked_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  reviewer_member_id         BIGINT NOT NULL,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_compliance_evidence_workspace_assessment_idx
  ON legal.ai_compliance_evidence (workspace_id, assessment_id);
CREATE INDEX IF NOT EXISTS idx_ai_compliance_evidence_workspace
  ON legal.ai_compliance_evidence (workspace_id);

-- from 30_ai_legal_source_corrections.up.sql §2 — cột kết luận + nguồn
ALTER TABLE legal.ai_compliance_evidence
  ADD COLUMN IF NOT EXISTS conclusion text NOT NULL DEFAULT 'COMPLIANT',
  ADD COLUMN IF NOT EXISTS source_version_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS rule_ids jsonb NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS legal.ai_provider_profiles (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  provider_key               TEXT NOT NULL,
  model_key                  TEXT NOT NULL,
  version                    TEXT NOT NULL,
  status                     TEXT NOT NULL CHECK (status IN ('DRAFT','APPROVED','SUSPENDED','REVOKED')),
  declared_processing_region TEXT NOT NULL,
  dpa_reference              TEXT,
  allowed_data_categories    JSONB NOT NULL DEFAULT '[]'::jsonb,
  reviewed_at                TIMESTAMPTZ,
  reviewed_by_member_id      BIGINT,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, provider_key, model_key, version)
);
CREATE INDEX IF NOT EXISTS ai_provider_profiles_workspace_status_idx
  ON legal.ai_provider_profiles (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_ai_provider_profiles_workspace
  ON legal.ai_provider_profiles (workspace_id);

CREATE TABLE IF NOT EXISTS legal.ai_data_processing_profiles (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  deployment_id              BIGINT NOT NULL REFERENCES legal.workspace_ai_deployments(id) ON DELETE CASCADE,
  binding_id                 BIGINT REFERENCES legal.ai_system_capability_bindings(id) ON DELETE SET NULL,
  purpose_id                 TEXT NOT NULL,
  data_categories            JSONB NOT NULL DEFAULT '[]'::jsonb,
  recipient_provider_profile_id BIGINT REFERENCES legal.ai_provider_profiles(id) ON DELETE RESTRICT,
  retention_policy_id        TEXT NOT NULL,
  transfer_conditions        JSONB NOT NULL DEFAULT '[]'::jsonb,
  minimization_required      BOOLEAN NOT NULL DEFAULT true,
  version                    TEXT NOT NULL,
  status                     TEXT NOT NULL CHECK (status IN ('DRAFT','ACTIVE','SUSPENDED','RETIRED')),
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_data_processing_profiles_workspace_deployment_idx
  ON legal.ai_data_processing_profiles (workspace_id, deployment_id);
CREATE INDEX IF NOT EXISTS idx_ai_data_processing_profiles_workspace
  ON legal.ai_data_processing_profiles (workspace_id);

CREATE TABLE IF NOT EXISTS legal.data_processing_authorizations (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  subject_reference_hash     TEXT NOT NULL,
  purpose_id                 TEXT NOT NULL,
  purpose_version            TEXT NOT NULL,
  authority_type             TEXT NOT NULL CHECK (authority_type IN ('CONSENT','CONTRACTUAL_NECESSITY','LEGAL_OBLIGATION','VITAL_INTERESTS','LEGITIMATE_INTERESTS')),
  proof_reference            TEXT NOT NULL,
  proof_hash                 TEXT NOT NULL,
  status                     TEXT NOT NULL CHECK (status IN ('GRANTED','WITHDRAWN','RESTRICTED')),
  granted_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  withdrawn_at               TIMESTAMPTZ,
  restricted_at              TIMESTAMPTZ,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS data_processing_authorizations_workspace_subject_idx
  ON legal.data_processing_authorizations (workspace_id, subject_reference_hash);
CREATE INDEX IF NOT EXISTS idx_data_processing_authorizations_workspace
  ON legal.data_processing_authorizations (workspace_id);

CREATE TABLE IF NOT EXISTS legal.data_subject_requests (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  subject_reference_hash     TEXT NOT NULL,
  request_type               TEXT NOT NULL CHECK (request_type IN ('ACCESS','CORRECTION','DELETION','RESTRICTION')),
  deadline                   TIMESTAMPTZ NOT NULL,
  status                     TEXT NOT NULL CHECK (status IN ('RECEIVED','IN_REVIEW','FULFILLED','REJECTED','LEGAL_HOLD')),
  result_summary             TEXT,
  legal_hold                 BOOLEAN NOT NULL DEFAULT false,
  legal_hold_reason          TEXT,
  handled_by_member_id       BIGINT,
  resolved_at                TIMESTAMPTZ,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS data_subject_requests_workspace_status_idx
  ON legal.data_subject_requests (workspace_id, status);
CREATE INDEX IF NOT EXISTS data_subject_requests_workspace_subject_idx
  ON legal.data_subject_requests (workspace_id, subject_reference_hash);
CREATE INDEX IF NOT EXISTS idx_data_subject_requests_workspace
  ON legal.data_subject_requests (workspace_id);

CREATE TABLE IF NOT EXISTS legal.ai_incidents (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  deployment_id              BIGINT NOT NULL REFERENCES legal.workspace_ai_deployments(id) ON DELETE CASCADE,
  severity                   TEXT NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
  status                     TEXT NOT NULL CHECK (status IN ('OPEN','CONTAINED','ASSESSING','NOTIFICATION_DECISION_PENDING','REMEDIATING','CLOSED')),
  detected_at                TIMESTAMPTZ NOT NULL,
  contained_at               TIMESTAMPTZ,
  closed_at                  TIMESTAMPTZ,
  data_categories            JSONB NOT NULL DEFAULT '[]'::jsonb,
  notification_deadline      TIMESTAMPTZ,
  notification_decision      TEXT CHECK (notification_decision IN ('NOT_REQUIRED','NOTIFY_AUTHORITY','NOTIFY_SUBJECTS','NOTIFY_BOTH')),
  notification_decision_at   TIMESTAMPTZ,
  notification_decision_by_member_id BIGINT,
  notification_rationale     TEXT,
  summary                    TEXT NOT NULL,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_incidents_workspace_deployment_idx
  ON legal.ai_incidents (workspace_id, deployment_id);
CREATE INDEX IF NOT EXISTS ai_incidents_workspace_status_idx
  ON legal.ai_incidents (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_ai_incidents_workspace
  ON legal.ai_incidents (workspace_id);

CREATE TABLE IF NOT EXISTS legal.ai_incident_actions (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  incident_id                BIGINT NOT NULL REFERENCES legal.ai_incidents(id) ON DELETE CASCADE,
  action_type                TEXT NOT NULL,
  description                TEXT NOT NULL,
  taken_by_member_id         BIGINT NOT NULL,
  evidence_reference         TEXT,
  evidence_hash              TEXT,
  taken_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_incident_actions_workspace_incident_idx
  ON legal.ai_incident_actions (workspace_id, incident_id);
CREATE INDEX IF NOT EXISTS idx_ai_incident_actions_workspace
  ON legal.ai_incident_actions (workspace_id);

CREATE TABLE IF NOT EXISTS legal.ai_compliance_snapshots (
  id                         BIGINT PRIMARY KEY,
  workspace_id               BIGINT NOT NULL,
  deployment_id              BIGINT NOT NULL REFERENCES legal.workspace_ai_deployments(id) ON DELETE CASCADE,
  assessment_id              BIGINT NOT NULL REFERENCES legal.ai_risk_assessments(id) ON DELETE CASCADE,
  mode                       TEXT NOT NULL CHECK (mode = 'ADVISORY_ONLY'),
  status                     TEXT NOT NULL CHECK (status IN ('DRAFT','ASSESSED','APPROVED_FOR_USE','SUSPENDED','REJECTED','RETIRED')),
  allowed_capabilities       JSONB NOT NULL DEFAULT '[]'::jsonb,
  provider_profile_version   TEXT NOT NULL,
  data_profile_version       TEXT NOT NULL,
  legal_version_ids          JSONB NOT NULL DEFAULT '[]'::jsonb,
  policy_snapshot_hash       TEXT NOT NULL,
  snapshot_hash              TEXT NOT NULL UNIQUE,
  issued_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at                 TIMESTAMPTZ NOT NULL,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_compliance_snapshots_workspace_deployment_idx
  ON legal.ai_compliance_snapshots (workspace_id, deployment_id);
CREATE INDEX IF NOT EXISTS ai_compliance_snapshots_workspace_hash_idx
  ON legal.ai_compliance_snapshots (workspace_id, snapshot_hash);
CREATE INDEX IF NOT EXISTS idx_ai_compliance_snapshots_workspace
  ON legal.ai_compliance_snapshots (workspace_id);

-- =========================================================================
-- from 30_ai_legal_source_corrections.up.sql §3 — ai_applicability_rules
-- (bảng quy tắc áp dụng AI chính quy gắn nguồn luật đã thẩm định)
-- =========================================================================
CREATE TABLE IF NOT EXISTS legal.ai_applicability_rules (
  id bigint PRIMARY KEY,
  rule_id text NOT NULL UNIQUE,
  rule_version text NOT NULL DEFAULT '1.0.0',
  regulation_source_id bigint NOT NULL REFERENCES legal.regulation_sources(id) ON DELETE CASCADE,
  regulation_version_id bigint NOT NULL REFERENCES legal.regulation_versions(id) ON DELETE CASCADE,
  source_content_hash text NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  review_status text NOT NULL DEFAULT 'REVIEWED',
  layer text NOT NULL,
  effect text NOT NULL,
  reason_code text NOT NULL,
  description text,
  predicate jsonb NOT NULL,
  mandatory_evidence_type text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

-- =========================================================================
-- from 29_ai_compliance_runtime_hardening.up.sql — defense-in-depth ở tầng DB
-- cho quyền sở hữu theo workspace. Nguyên tắc: composite UNIQUE (workspace_id, id)
-- trên bảng cha thuộc workspace + composite FK (workspace_id, <ref>) trên bảng
-- con -> PostgreSQL tự chặn insert/update cross-workspace.
--
-- Khác nguyên văn migration 29: bỏ NOT VALID + cặp VALIDATE CONSTRAINT (DB
-- baseline mới hoàn toàn rỗng, không có row lịch sử cần bỏ qua) và bỏ toàn bộ
-- backfill UPDATE — chỉ giữ phần cấu trúc.
-- =========================================================================

-- 1. Composite unique key trên các bảng cha thuộc workspace.
DO $$ BEGIN ALTER TABLE legal.workspace_ai_deployments ADD CONSTRAINT workspace_ai_deployments_workspace_id_id_key UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_risk_assessments ADD CONSTRAINT ai_risk_assessments_workspace_id_id_key UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_provider_profiles ADD CONSTRAINT ai_provider_profiles_workspace_id_id_key UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_incidents ADD CONSTRAINT ai_incidents_workspace_id_id_key UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_data_processing_profiles ADD CONSTRAINT ai_data_processing_profiles_workspace_id_id_key UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

-- 2. Composite foreign key trên bảng con -> parent(workspace_id, id).
DO $$ BEGIN ALTER TABLE legal.ai_risk_assessments ADD CONSTRAINT ai_risk_assessments_workspace_deployment_fk FOREIGN KEY (workspace_id, deployment_id) REFERENCES legal.workspace_ai_deployments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.workspace_ai_deployments ADD CONSTRAINT workspace_ai_deployments_workspace_assessment_fk FOREIGN KEY (workspace_id, current_assessment_id) REFERENCES legal.ai_risk_assessments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_evidence ADD CONSTRAINT ai_compliance_evidence_workspace_assessment_fk FOREIGN KEY (workspace_id, assessment_id) REFERENCES legal.ai_risk_assessments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_data_processing_profiles ADD CONSTRAINT ai_data_profiles_workspace_deployment_fk FOREIGN KEY (workspace_id, deployment_id) REFERENCES legal.workspace_ai_deployments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_data_processing_profiles ADD CONSTRAINT ai_data_profiles_workspace_provider_fk FOREIGN KEY (workspace_id, recipient_provider_profile_id) REFERENCES legal.ai_provider_profiles (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_incidents ADD CONSTRAINT ai_incidents_workspace_deployment_fk FOREIGN KEY (workspace_id, deployment_id) REFERENCES legal.workspace_ai_deployments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_incident_actions ADD CONSTRAINT ai_incident_actions_workspace_incident_fk FOREIGN KEY (workspace_id, incident_id) REFERENCES legal.ai_incidents (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_snapshots ADD CONSTRAINT ai_compliance_snapshots_workspace_deployment_fk FOREIGN KEY (workspace_id, deployment_id) REFERENCES legal.workspace_ai_deployments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_snapshots ADD CONSTRAINT ai_compliance_snapshots_workspace_assessment_fk FOREIGN KEY (workspace_id, assessment_id) REFERENCES legal.ai_risk_assessments (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;

-- 3. Snapshot provenance columns (migration 29 §3) — id thật của binding/evidence/
-- provider profile/data profile đã dùng để tạo snapshot + cờ provenance_complete.
ALTER TABLE legal.ai_compliance_snapshots
  ADD COLUMN IF NOT EXISTS capability_binding_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS evidence_hashes JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS provider_profile_id BIGINT,
  ADD COLUMN IF NOT EXISTS data_profile_id BIGINT,
  ADD COLUMN IF NOT EXISTS provenance_complete BOOLEAN NOT NULL DEFAULT false;

DO $$ BEGIN ALTER TABLE legal.ai_compliance_snapshots ADD CONSTRAINT ai_compliance_snapshots_workspace_provider_fk FOREIGN KEY (workspace_id, provider_profile_id) REFERENCES legal.ai_provider_profiles (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_snapshots ADD CONSTRAINT ai_compliance_snapshots_workspace_data_profile_fk FOREIGN KEY (workspace_id, data_profile_id) REFERENCES legal.ai_data_processing_profiles (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; WHEN duplicate_table THEN NULL; WHEN invalid_table_definition THEN NULL; END $$;
