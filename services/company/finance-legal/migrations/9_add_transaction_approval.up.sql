-- Approval gate cho giao dịch tài chính vượt ngưỡng rủi ro cao (CLAUDE.md §11:
-- high-risk actions phải qua permission/approval bằng deterministic code,
-- không chỉ dựa vào PolicyEngine/ApprovalService phía agentos vì endpoint
-- này có thể bị gọi trực tiếp, né qua tầng agent orchestrator).
ALTER TABLE finance.financial_transactions
  ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'AUTO_APPROVED',
  ADD COLUMN approved_by_user_id BIGINT,
  ADD COLUMN approved_at TIMESTAMPTZ;
