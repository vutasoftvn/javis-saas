// Capability id của agent (apps/cosa) mà endpoint Company chấp nhận qua delegation
// token. Phải khớp đúng id trong apps/cosa/capabilities/*.py và capability_refs của
// AgentSpec (apps/cosa/agents/specs.py). Endpoint không khai báo capability nào vẫn
// chỉ nhận phiên đăng nhập của người dùng.
//
// Cố ý CHƯA mở cho agent: finance.accounting_document.confirm và
// engagement.message.send (hành động rủi ro cao, cần người dùng tự thực hiện).
export const AGENT_CAP = Object.freeze({
  OPERATIONS_TASK_LIST: "operations.task.list",
  OPERATIONS_TASK_READ: "operations.task.read",
  OPERATIONS_TASK_CREATE_DRAFT: "operations.task.create_draft",
  STRATEGY_EVIDENCE_LIST: "strategy.evidence.list",
  FINANCE_CONNECTION_READ: "finance.connection.read",
  FINANCE_TRANSACTION_READ: "finance.transaction.read",
  FINANCE_TRANSACTION_RECORD: "finance.transaction.record",
  FINANCE_TRANSACTION_CLASSIFY_PROPOSE: "finance.transaction.classify_propose",
  FINANCE_ACCOUNTING_DOCUMENT_CREATE_DRAFT: "finance.accounting_document.create_draft",
  MARKETING_CONTEXT_READ: "commercial.marketing_context.read",
  CUSTOMER_360_READ: "commercial.customer_360.read",
  ENGAGEMENT_THREAD_READ: "engagement.thread.read",
  PROJECT_CRM_READ: "project.crm.read",
  VENTURE_PROFILE_READ: "venture.profile.read",
  LEGAL_ISSUE_READ: "legal.issue.read",
  PEOPLE_RISK_READ: "people.risk.read",
  PRODUCT_DECISION_READ: "product.decision.read",
  SECURITY_POSTURE_READ: "security.posture.read",
  DATA_GOVERNANCE_READ: "data.governance.read",
  AI_GOVERNANCE_READ: "ai.governance.read",
});
