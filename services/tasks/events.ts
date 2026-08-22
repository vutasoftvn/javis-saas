import { Topic } from "encore.dev/pubsub";
import { DomainEvent, makeDomainEvent, TASK_COMPLETED } from "../shared/events";
import type { Task } from "./task";

export interface TaskCompletedPayload {
  taskId: number;
  workspaceId: string;
}

export type TaskCompletedEvent = DomainEvent<typeof TASK_COMPLETED, TaskCompletedPayload>;

export const taskEvents = new Topic<TaskCompletedEvent>("task-events", {
  deliveryGuarantee: "at-least-once",
});

export function buildTaskCompletedEvent(task: Task): TaskCompletedEvent {
  return makeDomainEvent(TASK_COMPLETED, { taskId: task.id, workspaceId: task.workspaceId });
}
