-- Các dòng derived (LOI_NHUAN_GIU_LAI/LOI_NHUAN_GOP/THUE_TNDN/
-- LOI_NHUAN_SAU_THUE) được `ensureMappingSeeded` persist với bucket IS NULL —
-- đó chính là lý do migration up phải DROP NOT NULL. Phải xóa chúng TRƯỚC khi
-- khôi phục NOT NULL, nếu không `SET NOT NULL` sẽ fail ngay khi đã từng có
-- report được generate (đã kiểm chứng trên DB dev: 4 dòng null bucket).
DELETE FROM finance.accounting_report_mappings WHERE derived_kind IS NOT NULL;

ALTER TABLE finance.accounting_report_mappings
  DROP COLUMN IF EXISTS derived_kind,
  ALTER COLUMN bucket SET NOT NULL;

DROP TABLE IF EXISTS finance.tax_obligation_instances;
DROP TABLE IF EXISTS finance.accounting_policies;

-- Không tự động đổi 'opex' về 'cost' — rollback này chỉ khôi phục
-- schema, không khôi phục dữ liệu đã đổi tên (dữ liệu test only tại
-- thời điểm viết migration này).
