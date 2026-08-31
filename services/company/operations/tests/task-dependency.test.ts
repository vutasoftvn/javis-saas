import { describe, it, expect } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createTask } from "../handlers/task.handler";
import { createTaskDependency, listTaskDependencies, createTaskSchedule } from "../handlers/task-dependency.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
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
      workspaceId,
      authorization,
    });

    expect(dep.id).toBeDefined();
    expect(dep.taskId).toBe(taskB.id);
    expect(dep.dependsOnTaskId).toBe(taskA.id);
    expect(dep.status).toBe("PENDING");

    const list = await listTaskDependencies({ taskId: taskB.id, workspaceId, authorization });
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
      workspaceId,
      authorization,
    });

    expect(schedule.id).toBeDefined();
    expect(schedule.taskId).toBe(task.id);
    expect(schedule.cronExpr).toBe("0 9 * * 1-5");
    expect(schedule.active).toBe(true);
  });

  // M1 §4 — endpoint từng hoàn toàn không xác thực.
  it("rejects a dependency referencing a task from another workspace", async () => {
    const a = await makeAuthedWorkspace("Dep WS A");
    const b = await makeAuthedWorkspace("Dep WS B");

    const taskA = await createTask({
      workspaceId: a.workspaceId,
      title: "A task",
      authorization: a.authorization,
    });
    const taskB = await createTask({
      workspaceId: b.workspaceId,
      title: "B task",
      authorization: b.authorization,
    });

    // Caller B cố tạo dependency trỏ tới task của workspace A.
    await expect(
      createTaskDependency({
        taskId: taskB.id,
        dependsOnTaskId: taskA.id,
        dependencyType: "BLOCKS",
        workspaceId: b.workspaceId,
        authorization: b.authorization,
      })
    ).rejects.toThrow(/not in this workspace/i);
  });

  // M1 §4 — GET dependency listing từng không có auth/tenant scoping.
  it("rejects dependency listing without an access token", async () => {
    await expect(listTaskDependencies({ taskId: "123" } as any)).rejects.toThrow(/authorization/i);
  });

  it("does not list dependencies for a task in another workspace", async () => {
    const a = await makeAuthedWorkspace("Dependency Read A");
    const b = await makeAuthedWorkspace("Dependency Read B");
    const task = await createTask({ workspaceId: a.workspaceId, title: "private", authorization: a.authorization });

    await expect(listTaskDependencies({ taskId: task.id, workspaceId: b.workspaceId, authorization: b.authorization } as any))
      .rejects.toThrow(/not in this workspace|not found/i);
  });

  it("rejects an unauthenticated schedule creation", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Sched Auth WS");
    const task = await createTask({
      workspaceId,
      title: "T",
      authorization,
    });
    await expect(
      createTaskSchedule({
        taskId: task.id,
        scheduleType: "once",
        workspaceId,
        // no authorization
      })
    ).rejects.toThrow();
  });
});

