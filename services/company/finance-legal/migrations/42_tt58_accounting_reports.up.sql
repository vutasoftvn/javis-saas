-- Migration 42: F5 — TT58 accounting books & reports engine
-- (docs/superpowers/specs/2026-09-06-tt58-accounting-books-reports-design.md)
--
-- accounting_periods = "kỳ" (F1 posting lock, đã entity-scoped từ migration 35).
-- accounting_fiscal_profiles = chọn regime/mode TT58 cho một năm (migration 5).
-- Đây là 2 bảng khác nhau đã tồn tại — migration này mở rộng cả hai, không
-- tạo bảng "fiscal profile" hay "period" song song.

ALTER TABLE finance.accounting_periods
  ADD COLUMN IF NOT EXISTS fiscal_profile_id BIGINT
    REFERENCES finance.accounting_fiscal_profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

ALTER TABLE finance.accounting_fiscal_profiles
  ADD COLUMN IF NOT EXISTS legal_entity_id BIGINT,
  ADD COLUMN IF NOT EXISTS year_end DATE,
  ADD COLUMN IF NOT EXISTS mapping_version VARCHAR(50),
  ADD COLUMN IF NOT EXISTS applicability_decision_id BIGINT;

-- Unique cũ (workspace_id, fiscal_year) không phân biệt pháp nhân — đổi
-- sang unique index NULL-safe theo đúng kỹ thuật migration 38 (IA12).
ALTER TABLE finance.accounting_fiscal_profiles
  DROP CONSTRAINT IF EXISTS uix_fiscal_profile_workspace_year;

CREATE UNIQUE INDEX IF NOT EXISTS uix_fiscal_profile_workspace_entity_year
  ON finance.accounting_fiscal_profiles (workspace_id, COALESCE(legal_entity_id, 0), fiscal_year);

CREATE TABLE finance.accounting_report_mappings (
  id BIGINT PRIMARY KEY,
  regime_code VARCHAR(50) NOT NULL,
  mapping_version VARCHAR(50) NOT NULL,
  report_code VARCHAR(10) NOT NULL,
  line_code VARCHAR(20) NOT NULL,
  official_code VARCHAR(50) NOT NULL,
  name TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  rule_type VARCHAR(20) NOT NULL,
  bucket VARCHAR(20) NOT NULL,
  sign SMALLINT NOT NULL,
  rounding VARCHAR(20) NOT NULL,
  definition_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_report_mapping_line UNIQUE (regime_code, mapping_version, report_code, line_code)
);

CREATE TABLE finance.accounting_mapping_confirmations (
  id BIGINT PRIMARY KEY,
  regime_code VARCHAR(50) NOT NULL,
  mapping_version VARCHAR(50) NOT NULL,
  confirmed_by_member_id BIGINT NOT NULL,
  confirmed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_mapping_confirmation UNIQUE (regime_code, mapping_version)
);

CREATE TABLE finance.accounting_book_entries (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  legal_entity_id BIGINT NOT NULL,
  period_id BIGINT NOT NULL REFERENCES finance.accounting_periods(id) ON DELETE CASCADE,
  document_id BIGINT REFERENCES finance.accounting_documents(id) ON DELETE SET NULL,
  item TEXT NOT NULL,
  category VARCHAR(30) NOT NULL,
  amount_minor NUMERIC(38, 0) NOT NULL,
  currency VARCHAR(10) NOT NULL DEFAULT 'VND',
  effective_date DATE NOT NULL,
  source TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_book_entries_period ON finance.accounting_book_entries(period_id);
CREATE INDEX idx_book_entries_entity ON finance.accounting_book_entries(legal_entity_id);

CREATE TABLE finance.accounting_report_snapshots (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  legal_entity_id BIGINT NOT NULL,
  period_id BIGINT NOT NULL REFERENCES finance.accounting_periods(id) ON DELETE CASCADE,
  report_code VARCHAR(10) NOT NULL,
  mapping_version VARCHAR(50) NOT NULL,
  input_watermark TEXT NOT NULL,
  lines JSONB NOT NULL DEFAULT '[]',
  status VARCHAR(20) NOT NULL,
  issues JSONB NOT NULL DEFAULT '[]',
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_report_snapshots_period ON finance.accounting_report_snapshots(period_id, report_code);
