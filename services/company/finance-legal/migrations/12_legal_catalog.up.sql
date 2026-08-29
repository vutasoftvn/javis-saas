-- services/company/finance-legal/migrations/12_legal_catalog.up.sql
-- Regulation Sources & Versions catalog theo COSA One-Person Enterprise §3
CREATE SCHEMA IF NOT EXISTS legal;

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
