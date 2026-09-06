-- Migration 45: F6b — mở rộng engine TT58 (tồn kho, COGS/opex, thuế TNDN,
-- chính sách kế toán, nghĩa vụ thuế). Xem
-- docs/superpowers/specs/2026-09-06-f6b-tt58-report-expansion-and-flutter-wiring-design.md

-- Đổi tên category 'cost' cũ thành 'opex' — F5 mới chạy vài giờ, chỉ có
-- dữ liệu test, an toàn để rename thẳng (hành vi classifyBookEntry cho
-- 'opex' kế thừa đúng công thức 'cost' cũ, xem Task 3).
UPDATE finance.accounting_book_entries SET category = 'opex' WHERE category = 'cost';

CREATE TABLE finance.accounting_policies (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  legal_entity_id BIGINT NOT NULL,
  inventory_valuation_method VARCHAR(50) NOT NULL DEFAULT 'weighted_average',
  depreciation_method VARCHAR(50) NOT NULL DEFAULT 'straight_line',
  revenue_recognition_method TEXT NOT NULL DEFAULT
    'Ghi nhận khi hoàn thành chuyển giao dịch vụ/hàng hóa',
  corporate_income_tax_rate_bps INTEGER,
  confirmed_by_member_id BIGINT,
  confirmed_at TIMESTAMPTZ,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_accounting_policy_entity UNIQUE (workspace_id, legal_entity_id)
);

CREATE TABLE finance.tax_obligation_instances (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  legal_entity_id BIGINT NOT NULL,
  period_id BIGINT NOT NULL REFERENCES finance.accounting_periods(id) ON DELETE CASCADE,
  tax_name VARCHAR(100) NOT NULL,
  incurred_minor NUMERIC(38, 0) NOT NULL DEFAULT 0,
  paid_minor NUMERIC(38, 0) NOT NULL DEFAULT 0,
  source VARCHAR(20) NOT NULL DEFAULT 'MANUAL',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_tax_obligation UNIQUE (workspace_id, legal_entity_id, period_id, tax_name)
);

ALTER TABLE finance.accounting_report_mappings
  ALTER COLUMN bucket DROP NOT NULL,
  ADD COLUMN IF NOT EXISTS derived_kind VARCHAR(30);
