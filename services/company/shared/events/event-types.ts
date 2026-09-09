// Canonical business-event types — past tense, "domain.entity.action.vN".
// Xem docs/architecture/adr/ADR-LOCAL-FIRST-001-...md + event-envelope.schema.json.
export const OPERATIONS_TASK_CREATED_V1 = "operations.task.created.v1";
export const OPERATIONS_TASK_COMPLETED_V1 = "operations.task.completed.v1";
// Signed Company→Agent work-package dispatch (Task 3). Payload chỉ mang opaque
// IDs + priority + expected capability refs + correlation ID.
export const OPERATING_WORK_PACKAGE_QUEUED_V1 = "operating.work_package.queued.v1";
export const OPERATING_WORK_PACKAGE_REASSIGN_REQUESTED_V1 =
  "operating.work_package.reassign_requested.v1";

export type CanonicalEventType =
  | typeof OPERATIONS_TASK_CREATED_V1
  | typeof OPERATIONS_TASK_COMPLETED_V1
  | typeof OPERATING_WORK_PACKAGE_QUEUED_V1
  | typeof OPERATING_WORK_PACKAGE_REASSIGN_REQUESTED_V1;

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
  title: string;
  status: string;
}

export interface TaskCompletedPayloadV1 {
  taskId: string;
  workspaceId: string;
  completedAt: string;
}
