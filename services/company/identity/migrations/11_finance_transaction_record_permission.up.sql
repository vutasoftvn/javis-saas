-- Migration 11: Finance transaction record permission definition

INSERT INTO core.permission_definitions (permission_key, domain, description) VALUES
  ('finance.transaction.record', 'finance', 'Ghi nhận giao dịch tài chính (thu/chi) vào sổ sách')
ON CONFLICT (permission_key) DO NOTHING;
