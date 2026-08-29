-- services/company/finance-legal/migrations/13_legal_applicability_obligations.up.sql
-- Applicability rules, obligation templates & instances, entity profiles

CREATE TABLE IF NOT EXISTS legal.legal_entity_profiles (
  id                    BIGINT PRIMARY KEY,
  workspace_id          BIGINT NOT NULL,
  platform_company_id   TEXT,
  entity_type           TEXT NOT NULL,
  status                TEXT NOT NULL DEFAULT 'NOT_DECLARED'
                          CHECK (status IN ('NOT_DECLARED','UNREGISTERED','REGISTRATION_READINESS','REGISTERED_PENDING_VERIFICATION','REGISTERED_VERIFIED')),
  registration_number   TEXT,
  tax_id                TEXT,
  verified_by_member_id BIGINT,
  verified_at           TIMESTAMPTZ,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_legal_entity_profiles_workspace
  ON legal.legal_entity_profiles(workspace_id);

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
