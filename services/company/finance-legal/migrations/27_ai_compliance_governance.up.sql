-- services/company/finance-legal/migrations/27_ai_compliance_governance.up.sql
-- AI compliance & governance tables for COSA private-business advisory mode

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

ALTER TABLE legal.workspace_ai_deployments
  ADD CONSTRAINT fk_workspace_ai_deployments_assessment
  FOREIGN KEY (current_assessment_id)
  REFERENCES legal.ai_risk_assessments(id)
  ON DELETE SET NULL;

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
