import { describe, expect, it } from "vitest";
import { buildTaskCompletedEvent } from "./events";
import type { Task } from "./task";

describe("buildTaskCompletedEvent", () => {
  it("builds a task.completed event from a task", () => {
    const task: Task = {
      id: 1,
      workspaceId: "ws1",
      title: "x",
      status: "completed",
      priority: "medium",
      dueDate: null,
      createdAt: "2026-01-01T00:00:00.000Z",
      updatedAt: "2026-01-01T00:00:00.000Z",
    };
    const event = buildTaskCompletedEvent(task);
    expect(event.name).toBe("task.completed");
    expect(event.payload).toEqual({ taskId: 1, workspaceId: "ws1" });
  });
});
