// Canonical business-event types — past tense, "domain.entity.action.vN".
// Xem docs/architecture/adr/ADR-LOCAL-FIRST-001-...md + event-envelope.schema.json.
export const OPERATIONS_TASK_CREATED_V1 = "operations.task.created.v1";
export const OPERATIONS_TASK_COMPLETED_V1 = "operations.task.completed.v1";

export type CanonicalEventType =
  | typeof OPERATIONS_TASK_CREATED_V1
  | typeof OPERATIONS_TASK_COMPLETED_V1;

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
