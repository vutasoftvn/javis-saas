-- Revert M7 §8.
ALTER TABLE finance.financial_snapshots
  DROP COLUMN IF EXISTS opening_balance,
  DROP COLUMN IF EXISTS current_cash,
  DROP COLUMN IF EXISTS monthly_net_burn,
  DROP COLUMN IF EXISTS burn_window_months,
  DROP COLUMN IF EXISTS cash_flow_positive;
