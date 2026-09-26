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
  // Startup OS (plan 2026-09-18 Phase 3): onboarding hội thoại /cs:setup, /cs:update
  // và tư vấn Goal. Agent chỉ ghi ngữ cảnh do chính Founder khai báo trong chat;
  // tạo Goal và triage Project vẫn do Founder thao tác (không mở cho agent).
  STARTUP_OS_CONTEXT_READ: "startup_os.onboard.context_read",
  STARTUP_OS_CADENCE_STATUS: "startup_os.onboard.cadence_status",
  STARTUP_OS_CADENCE_ADVISORY: "startup_os.onboard.cadence_advisory",
  STARTUP_OS_SESSION_START: "startup_os.onboard.session_start",
  STARTUP_OS_DIMENSION_UPDATE: "startup_os.onboard.dimension_update",
  STARTUP_OS_SNAPSHOT_CREATE: "startup_os.onboard.snapshot_create",
  STARTUP_OS_GOAL_TREE_READ: "startup_os.goal.tree_read",
  STARTUP_OS_GOALS_NEEDING_REVIEW: "startup_os.goal.needing_review",
  STARTUP_OS_GOAL_ADVISORY: "startup_os.goal.advisory",
});
