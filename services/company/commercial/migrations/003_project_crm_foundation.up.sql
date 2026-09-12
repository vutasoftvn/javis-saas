-- Migration 003: Project CRM Foundation
-- Adds Project-scoped lead sources, custom field definitions, field values, identity keys,
-- ingestion events, dedup candidates, consents, and capture forms under schema `sales`.

CREATE TABLE IF NOT EXISTS sales.lead_sources (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  source_type TEXT NOT NULL,
  label TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  configuration_revision INTEGER NOT NULL DEFAULT 1,
  created_by BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT fk_lead_sources_proj_ws FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lead_sources_ws_proj
  ON sales.lead_sources (workspace_id, project_id);

CREATE TABLE IF NOT EXISTS sales.lead_field_definitions (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  stable_key TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  label TEXT NOT NULL,
  data_type TEXT NOT NULL,
  validation_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  allowed_values_json JSONB,
  required_at_stages_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  classification TEXT NOT NULL DEFAULT 'BUSINESS_CONFIDENTIAL',
  agent_input_allowed BOOLEAN NOT NULL DEFAULT true,
  searchable BOOLEAN NOT NULL DEFAULT true,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  created_by BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  retired_at TIMESTAMPTZ,
  CONSTRAINT uix_lead_field_definitions_ws_proj_key_ver UNIQUE (workspace_id, project_id, stable_key, version),
  CONSTRAINT fk_lead_field_definitions_proj_ws FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lead_field_definitions_ws_proj
  ON sales.lead_field_definitions (workspace_id, project_id);

CREATE TABLE IF NOT EXISTS sales.project_lead_capture_forms (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  lead_source_id BIGINT NOT NULL REFERENCES sales.lead_sources(id) ON DELETE CASCADE,
  form_key TEXT NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1,
  active BOOLEAN NOT NULL DEFAULT true,
  allowed_field_definition_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  required_consent_purpose TEXT NOT NULL,
  required_consent_version TEXT NOT NULL,
  public_verification_key_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_lead_capture_forms_ws_proj_key UNIQUE (workspace_id, project_id, form_key),
  CONSTRAINT fk_lead_capture_forms_proj_ws FOREIGN KEY (project_id, workspace_id) REFERENCES strategy.projects(id, workspace_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lead_capture_forms_ws_proj
  ON sales.project_lead_capture_forms (workspace_id, project_id);

CREATE TABLE IF NOT EXISTS sales.lead_ingestion_events (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  lead_source_id BIGINT NOT NULL REFERENCES sales.lead_sources(id) ON DELETE CASCADE,
  capture_form_id BIGINT REFERENCES sales.project_lead_capture_forms(id) ON DELETE SET NULL,
  external_event_id TEXT NOT NULL,
  payload_digest TEXT NOT NULL,
  signature_key_id TEXT,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  lead_id BIGINT REFERENCES sales.sales_leads(id) ON DELETE SET NULL,
  CONSTRAINT uix_lead_ingestion_events_ws_source_ext UNIQUE (workspace_id, lead_source_id, external_event_id)
);

CREATE INDEX IF NOT EXISTS idx_lead_ingestion_events_ws_proj
  ON sales.lead_ingestion_events (workspace_id, project_id);

-- Thêm nullable lead_source_id và provenance_event_id vào sales.sales_leads
ALTER TABLE sales.sales_leads
  ADD COLUMN IF NOT EXISTS lead_source_id BIGINT REFERENCES sales.lead_sources(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS provenance_event_id BIGINT REFERENCES sales.lead_ingestion_events(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS sales.lead_field_values (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  lead_id BIGINT NOT NULL REFERENCES sales.sales_leads(id) ON DELETE CASCADE,
  field_definition_id BIGINT NOT NULL REFERENCES sales.lead_field_definitions(id) ON DELETE CASCADE,
  value_json JSONB NOT NULL,
  normalized_search_value TEXT,
  source_kind TEXT NOT NULL DEFAULT 'manual',
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_lead_field_values_lead_def UNIQUE (lead_id, field_definition_id)
);

CREATE INDEX IF NOT EXISTS idx_lead_field_values_ws_proj_lead
  ON sales.lead_field_values (workspace_id, project_id, lead_id);

CREATE INDEX IF NOT EXISTS idx_lead_field_values_norm_search
  ON sales.lead_field_values (normalized_search_value);

CREATE TABLE IF NOT EXISTS sales.lead_identity_keys (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  lead_id BIGINT NOT NULL REFERENCES sales.sales_leads(id) ON DELETE CASCADE,
  key_type TEXT NOT NULL,
  key_hash TEXT NOT NULL,
  key_version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_lead_identity_keys_ws_type_ver_hash UNIQUE (workspace_id, key_type, key_version, key_hash)
);

CREATE INDEX IF NOT EXISTS idx_lead_identity_keys_ws_proj_lead
  ON sales.lead_identity_keys (workspace_id, project_id, lead_id);

CREATE TABLE IF NOT EXISTS sales.lead_dedup_candidates (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  incoming_lead_id BIGINT NOT NULL REFERENCES sales.sales_leads(id) ON DELETE CASCADE,
  existing_lead_id BIGINT NOT NULL REFERENCES sales.sales_leads(id) ON DELETE CASCADE,
  reason_codes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  state TEXT NOT NULL DEFAULT 'NEEDS_REVIEW',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_by BIGINT,
  resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_lead_dedup_candidates_ws_proj_state
  ON sales.lead_dedup_candidates (workspace_id, project_id, state);

CREATE TABLE IF NOT EXISTS sales.lead_consents (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  lead_id BIGINT NOT NULL REFERENCES sales.sales_leads(id) ON DELETE CASCADE,
  purpose TEXT NOT NULL,
  lawful_basis TEXT NOT NULL,
  consent_state TEXT NOT NULL DEFAULT 'GRANTED',
  policy_version TEXT NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at TIMESTAMPTZ,
  provenance_event_id BIGINT REFERENCES sales.lead_ingestion_events(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_lead_consents_ws_proj_lead
  ON sales.lead_consents (workspace_id, project_id, lead_id);
