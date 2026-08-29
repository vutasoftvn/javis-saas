-- services/company/finance-legal/migrations/11_financial_snapshot_calc_v2.up.sql
-- M7 §8 — sửa finance calculation:
--   current_cash = opening_balance + Σ transactions tới snapshot_date (số dư THẬT)
--   monthly_net_burn = burn theo cửa sổ trailing (mặc định 3 tháng), KHÔNG tổng lịch sử
--   runway = current_cash / monthly_net_burn khi >0; cash-flow dương ⇒ runway NULL +
--            cash_flow_positive=true (BỎ hard-code 99).

ALTER TABLE finance.financial_snapshots
  ADD COLUMN IF NOT EXISTS opening_balance    NUMERIC(20, 2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS current_cash       NUMERIC(20, 2),
  ADD COLUMN IF NOT EXISTS monthly_net_burn   NUMERIC(20, 2),
  ADD COLUMN IF NOT EXISTS burn_window_months INTEGER NOT NULL DEFAULT 3,
  ADD COLUMN IF NOT EXISTS cash_flow_positive BOOLEAN NOT NULL DEFAULT false;

-- Xoá các runway hard-code 99 (breakeven/positive) khỏi dữ liệu cũ — để service
-- tính lại đúng ở lần snapshot kế tiếp.
UPDATE finance.financial_snapshots
  SET runway_months = NULL, cash_flow_positive = true
  WHERE runway_months = 99 OR runway_months = 99.00;
