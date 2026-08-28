import { randomUUID } from "node:crypto";
import { makeBusinessEvent, BusinessEventEnvelope } from "../../shared/events/envelope";
import {
  OPERATIONS_TASK_CREATED_V1,
  OPERATIONS_TASK_COMPLETED_V1,
  TaskCreatedPayloadV1,
  TaskCompletedPayloadV1,
} from "../../shared/events/event-types";
import type { Task } from "../handlers/task.handler";

export interface EventContext {
  correlationId?: string;
  causationId?: string;
  actor?: { kind: "user" | "agent" | "system"; id: string };
}

export function buildTaskCreatedEvent(
  task: Task,
  ctx?: EventContext
): BusinessEventEnvelope<TaskCreatedPayloadV1> {
  const correlationId = ctx?.correlationId || randomUUID();
  const actor = ctx?.actor || { kind: "system", id: "operations" };
  return makeBusinessEvent({
    eventType: OPERATIONS_TASK_CREATED_V1,
    workspaceId: task.workspaceId,
    aggregateType: "task",
    aggregateId: task.id,
    correlationId,
    causationId: ctx?.causationId,
    actor,
    classification: "internal",
    payload: {
      taskId: task.id,
      workspaceId: task.workspaceId,
      title: task.title,
      status: task.status,
    },
  });
}

export function buildTaskCompletedEvent(
  task: Task,
  ctx?: EventContext
): BusinessEventEnvelope<TaskCompletedPayloadV1> {
  const correlationId = ctx?.correlationId || randomUUID();
  const actor = ctx?.actor || { kind: "system", id: "operations" };
  return makeBusinessEvent({
    eventType: OPERATIONS_TASK_COMPLETED_V1,
    workspaceId: task.workspaceId,
    aggregateType: "task",
    aggregateId: task.id,
    correlationId,
    causationId: ctx?.causationId,
    actor,
    classification: "internal",
    payload: {
      taskId: task.id,
      workspaceId: task.workspaceId,
      completedAt: new Date().toISOString(),
    },
  });
}
