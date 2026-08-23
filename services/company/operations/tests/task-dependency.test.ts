import { describe, it, expect } from "vitest";
import { registerUserService } from "../../identity/services/auth.service";
import { createTask } from "../handlers/task.handler";
import { createTaskDependency, listTaskDependencies, createTaskSchedule } from "../handlers/task-dependency.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await registerUserService({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    password: "password123",
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("Task Dependencies & Schedules Service", () => {
  it("creates a dependency between two tasks and lists it", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Dependency Test WS");

    const taskA = await createTask({
      workspaceId,
      title: "Task A: Setup Database Schema",
      authorization,
    });

    const taskB = await createTask({
      workspaceId,
      title: "Task B: Run Migration",
      authorization,
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
    const { workspaceId, authorization } = await makeAuthedWorkspace("Schedule Test WS");

    const task = await createTask({
      workspaceId,
      title: "Daily Standup AI Summary",
      authorization,
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

