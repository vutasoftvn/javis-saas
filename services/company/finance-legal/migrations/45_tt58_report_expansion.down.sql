ALTER TABLE finance.accounting_report_mappings
  DROP COLUMN IF EXISTS derived_kind,
  ALTER COLUMN bucket SET NOT NULL;

DROP TABLE IF EXISTS finance.tax_obligation_instances;
DROP TABLE IF EXISTS finance.accounting_policies;

-- Không tự động đổi 'opex' về 'cost' — rollback này chỉ khôi phục
-- schema, không khôi phục dữ liệu đã đổi tên (dữ liệu test only tại
-- thời điểm viết migration này).
