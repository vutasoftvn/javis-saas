ALTER TABLE finance.payment_requests
  DROP COLUMN IF EXISTS budget_override_by_member_id,
  DROP COLUMN IF EXISTS budget_override_reason;

DROP TABLE IF EXISTS finance.project_budget_envelopes;
