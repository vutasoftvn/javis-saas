// Canonical business-event types — past tense, "domain.entity.action.vN".
// Xem docs/architecture/adr/ADR-LOCAL-FIRST-001-...md + event-envelope.schema.json.
export const OPERATIONS_TASK_CREATED_V1 = "operations.task.created.v1";
export const OPERATIONS_TASK_COMPLETED_V1 = "operations.task.completed.v1";
// Signed Company→Agent work-package dispatch (Task 3). Payload chỉ mang opaque
// IDs + priority + expected capability refs + correlation ID.
export const OPERATING_WORK_PACKAGE_QUEUED_V1 = "operating.work_package.queued.v1";
export const OPERATING_WORK_PACKAGE_REASSIGN_REQUESTED_V1 =
  "operating.work_package.reassign_requested.v1";

// Project-scoped business events (Founder Activity Feed, Task 4)
export const OPERATIONS_WORK_PACKAGE_CREATED_V1 = "operations.work_package.created.v1";
export const OPERATIONS_DECISION_RECORDED_V1 = "operations.decision.recorded.v1";
export const OPERATIONS_EVIDENCE_LINKED_V1 = "operations.evidence.linked.v1";
export const OPERATIONS_RISK_RAISED_V1 = "operations.risk.raised.v1";
export const OPERATIONS_RISK_RESOLVED_V1 = "operations.risk.resolved.v1";
export const OPERATIONS_PROJECT_AGENT_ASSIGNMENT_ACTIVATED_V1 =
  "operations.project_agent_assignment.activated.v1";
export const OPERATIONS_PROJECT_AGENT_ASSIGNMENT_PAUSED_V1 =
  "operations.project_agent_assignment.paused.v1";
export const EXECUTIVE_DELIBERATION_FRAMED_V1 =
  "executive.deliberation.framed.v1";
export const EXECUTIVE_ANALYSIS_COMPLETED_V1 =
  "executive.analysis.completed.v1";
export const EXECUTIVE_ANALYSIS_FAILED_V1 =
  "executive.analysis.failed.v1";

export type CanonicalEventType =
  | typeof OPERATIONS_TASK_CREATED_V1
  | typeof OPERATIONS_TASK_COMPLETED_V1
  | typeof OPERATING_WORK_PACKAGE_QUEUED_V1
  | typeof OPERATING_WORK_PACKAGE_REASSIGN_REQUESTED_V1
  | typeof OPERATIONS_WORK_PACKAGE_CREATED_V1
  | typeof OPERATIONS_DECISION_RECORDED_V1
  | typeof OPERATIONS_EVIDENCE_LINKED_V1
  | typeof OPERATIONS_RISK_RAISED_V1
  | typeof OPERATIONS_RISK_RESOLVED_V1
  | typeof OPERATIONS_PROJECT_AGENT_ASSIGNMENT_ACTIVATED_V1
  | typeof OPERATIONS_PROJECT_AGENT_ASSIGNMENT_PAUSED_V1
  | typeof EXECUTIVE_DELIBERATION_FRAMED_V1
  | typeof EXECUTIVE_ANALYSIS_COMPLETED_V1
  | typeof EXECUTIVE_ANALYSIS_FAILED_V1;

export interface WorkPackageQueuedPayloadV1 {
  workspaceId: string;
  workPackageId: string;
  workAttemptId: string;
  agentInstanceId: string;
  assignmentId: string;
  effectivePriority: "P0" | "P1" | "P2" | "P3";
  expectedCapabilityRefs: string[];
  correlationId: string;
}

// Payload chỉ chứa IDs + changed state; consumer re-read chi tiết qua capability.
export interface TaskCreatedPayloadV1 {
  taskId: string;
  workspaceId: string;
  project_id?: string;
  title: string;
  status: string;
}

export interface TaskCompletedPayloadV1 {
  taskId: string;
  workspaceId: string;
  project_id?: string;
  completedAt: string;
}

// Project-scoped event payloads (Founder Activity Feed)
export interface WorkPackageCreatedPayloadV1 {
  workPackageId: string;
  taskId: string;
  project_id?: string;
  status: string;
}

export interface DecisionRecordedPayloadV1 {
  decision_id?: string;
  project_id?: string;
  decision: string;
  status: string;
}

export interface EvidenceLinkedPayloadV1 {
  evidence_ref?: string;
  project_id?: string;
  sourceType: string;
  status: string;
}

export interface RiskRaisedPayloadV1 {
  risk_id?: string;
  project_id?: string;
  title?: string;
  status: string;
}

export interface RiskResolvedPayloadV1 {
  risk_id?: string;
  project_id?: string;
  title?: string;
  status: string;
}
