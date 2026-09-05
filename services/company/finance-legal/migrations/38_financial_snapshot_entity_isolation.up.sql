-- Migration 38: Financial snapshot entity isolation (IA12)
--
-- Migration 35 thêm cột legal_entity_id vào financial_snapshots nhưng unique
-- constraint (workspace_id, snapshot_date, currency) KHÔNG gồm entity — 2
-- pháp nhân khác nhau trong cùng workspace không thể cùng có snapshot ở
-- cùng ngày/currency (INSERT thứ 2 vi phạm unique constraint dù application
-- code đã lọc theo legal_entity_id đúng ở tầng service). Dùng unique INDEX
-- với COALESCE thay vì unique CONSTRAINT thuần vì Postgres coi NULL khác
-- NULL trong unique constraint — snapshot cấp workspace (legal_entity_id
-- NULL) cần vẫn bị giới hạn tối đa 1 dòng/ngày/currency, không được phép
-- NULL trùng vô hạn.

ALTER TABLE finance.financial_snapshots
  DROP CONSTRAINT IF EXISTS financial_snapshots_workspace_snapshot_currency_key;

CREATE UNIQUE INDEX IF NOT EXISTS financial_snapshots_workspace_snapshot_currency_entity_key
  ON finance.financial_snapshots (workspace_id, snapshot_date, currency, COALESCE(legal_entity_id, 0));
