-- Rollback migration 43: trả accounting_mapping_confirmations về xác nhận
-- toàn cục theo (regime_code, mapping_version).
--
-- Xoá dữ liệu trước khi khôi phục unique constraint cũ: sau migration 43 mỗi
-- workspace có thể có hàng xác nhận riêng cho cùng một mapping_version, nên
-- gộp ngược lại sẽ vi phạm unique (regime_code, mapping_version). Dữ liệu
-- tiền-launch, xoá là an toàn (xem phần up).
DELETE FROM finance.accounting_mapping_confirmations;

ALTER TABLE finance.accounting_mapping_confirmations
  DROP CONSTRAINT IF EXISTS uix_mapping_confirmation;

ALTER TABLE finance.accounting_mapping_confirmations
  ADD CONSTRAINT uix_mapping_confirmation
    UNIQUE (regime_code, mapping_version);

ALTER TABLE finance.accounting_mapping_confirmations
  DROP COLUMN IF EXISTS workspace_id;
