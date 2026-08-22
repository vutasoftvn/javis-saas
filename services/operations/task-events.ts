import { Topic } from "encore.dev/pubsub";
import { DomainEvent, makeDomainEvent, TASK_COMPLETED, TASK_CREATED } from "../shared/events";
import type { Task } from "./task";

export interface TaskCreatedPayload {
  taskId: number;
  workspaceId: number;
}

export interface TaskCompletedPayload {
  taskId: number;
  workspaceId: number;
}

export type TaskCreatedEvent = DomainEvent<typeof TASK_CREATED, TaskCreatedPayload>;
export type TaskCompletedEvent = DomainEvent<typeof TASK_COMPLETED, TaskCompletedPayload>;
export type TaskEvent = TaskCreatedEvent | TaskCompletedEvent;

export const taskEvents = new Topic<TaskEvent>("task-events", {
  deliveryGuarantee: "at-least-once",
});

export function buildTaskCreatedEvent(task: Task): TaskCreatedEvent {
  return makeDomainEvent(TASK_CREATED, { taskId: task.id, workspaceId: task.workspaceId });
}

export function buildTaskCompletedEvent(task: Task): TaskCompletedEvent {
  return makeDomainEvent(TASK_COMPLETED, { taskId: task.id, workspaceId: task.workspaceId });
}
