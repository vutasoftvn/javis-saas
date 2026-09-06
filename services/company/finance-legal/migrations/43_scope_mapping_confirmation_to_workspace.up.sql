-- Migration 43: gắn accounting_mapping_confirmations vào workspace (fix C1)
--
-- Bản migration 42 tạo bảng này với unique (regime_code, mapping_version) —
-- tức xác nhận mapping là TOÀN CỤC. Hệ quả là lỗ hổng phân quyền chéo tenant:
-- founder của MỘT workspace bất kỳ gọi
-- `POST /finance/accounting-mapping/:regimeCode/:mappingVersion/confirm` là
-- report của MỌI workspace khác dùng cùng mapping_version lập tức nhảy sang
-- `status=VERIFIED`, dù founder đó không có quan hệ/thẩm quyền gì với các
-- tenant kia. Xác nhận phải thuộc về từng workspace.

ALTER TABLE finance.accounting_mapping_confirmations
  ADD COLUMN IF NOT EXISTS workspace_id BIGINT;

-- Bảng này mới có từ migration 42 (chưa launch) và tới nay chỉ được ghi bởi
-- các lần chạy test trên DB dev — không có dữ liệu người dùng thật. Xoá sạch
-- thay vì backfill, vì không tồn tại cách suy ra workspace nào đã xác nhận
-- một hàng toàn cục; founder sẽ xác nhận lại theo đúng workspace của mình.
DELETE FROM finance.accounting_mapping_confirmations;

ALTER TABLE finance.accounting_mapping_confirmations
  ALTER COLUMN workspace_id SET NOT NULL;

ALTER TABLE finance.accounting_mapping_confirmations
  DROP CONSTRAINT IF EXISTS uix_mapping_confirmation;

ALTER TABLE finance.accounting_mapping_confirmations
  ADD CONSTRAINT uix_mapping_confirmation
    UNIQUE (workspace_id, regime_code, mapping_version);
