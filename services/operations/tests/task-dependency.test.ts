import { describe, it, expect } from "vitest";
import { createWorkspace } from "../../identity/handlers/workspace.handler";
import { createTask } from "../handlers/task.handler";
import { createTaskDependency, listTaskDependencies, createTaskSchedule } from "../handlers/task-dependency.handler";

describe("Task Dependencies & Schedules Service", () => {
  it("creates a dependency between two tasks and lists it", async () => {
    const ws = await createWorkspace({ name: "Dependency Test WS" });
    const workspaceId = ws.id;

    const taskA = await createTask({
      workspaceId,
      title: "Task A: Setup Database Schema",
    });

    const taskB = await createTask({
      workspaceId,
      title: "Task B: Run Migration",
    });

    const dep = await createTaskDependency({
      taskId: taskB.id,
      dependsOnTaskId: taskA.id,
      dependencyType: "BLOCKS",
    });

    expect(dep.id).toBeDefined();
    expect(dep.taskId).toBe(taskB.id);
    expect(dep.dependsOnTaskId).toBe(taskA.id);
    expect(dep.status).toBe("PENDING");

    const list = await listTaskDependencies({ taskId: taskB.id });
    expect(list.dependencies.some((d) => d.id === dep.id)).toBe(true);
  });

  it("creates a schedule for a task", async () => {
    const ws = await createWorkspace({ name: "Schedule Test WS" });
    const workspaceId = ws.id;

    const task = await createTask({
      workspaceId,
      title: "Daily Standup AI Summary",
    });

    const schedule = await createTaskSchedule({
      taskId: task.id,
      scheduleType: "recurring",
      cronExpr: "0 9 * * 1-5",
    });

    expect(schedule.id).toBeDefined();
    expect(schedule.taskId).toBe(task.id);
    expect(schedule.cronExpr).toBe("0 9 * * 1-5");
    expect(schedule.active).toBe(true);
  });
});
