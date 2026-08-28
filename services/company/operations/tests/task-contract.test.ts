import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  createTask,
  getTask,
  listTasks,
  updateTaskStatus,
} from "../handlers/task.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  const authorization = `Bearer ${user.accessToken}`;
  const ctx = await requireWorkspaceAccess(authorization, user.workspaceId);
  return { workspaceId: user.workspaceId, authorization, ctx, user };
}

describe("Operations Task API Contract", () => {
  it("createTask: creates a new task and returns complete DTO", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Task Contract WS 1");

    const task = await createTask({
      workspaceId,
      title: "Write documentation",
      priority: "high",
      dueAt: "2026-09-01",
      authorization,
    });

    expect(task).toBeDefined();
    expect(task.id).toBeDefined();
    expect(task.workspaceId).toBe(workspaceId);
    expect(task.title).toBe("Write documentation");
    expect(task.status).toBe("todo");
    expect(task.priority).toBe("high");
    expect(task.dueAt).toContain("2026-09-01");
    expect(task.createdAt).toBeDefined();
    expect(task.updatedAt).toBeDefined();

  });

  it("listTasks: returns { tasks: Task[] } scoped to caller's workspace", async () => {
    const wsA = await makeAuthedWorkspace("Task List WS A");
    const wsB = await makeAuthedWorkspace("Task List WS B");

    const taskA = await createTask({
      workspaceId: wsA.workspaceId,
      title: "Task only in WS A",
      authorization: wsA.authorization,
    });

    const taskB = await createTask({
      workspaceId: wsB.workspaceId,
      title: "Task only in WS B",
      authorization: wsB.authorization,
    });

    const resA = await listTasks({
      workspaceId: wsA.workspaceId,
      authorization: wsA.authorization,
    });

    expect(resA.tasks.map((t) => t.id)).toContain(taskA.id);
    expect(resA.tasks.map((t) => t.id)).not.toContain(taskB.id);
  });

  it("getTask: fetches single task and enforces tenant isolation (404 on cross-workspace)", async () => {
    const wsA = await makeAuthedWorkspace("Task Get WS A");
    const wsB = await makeAuthedWorkspace("Task Get WS B");

    const taskB = await createTask({
      workspaceId: wsB.workspaceId,
      title: "Task in WS B",
      authorization: wsB.authorization,
    });

    // wsB caller can get taskB
    const fetched = await getTask({
      id: taskB.id,
      workspaceId: wsB.workspaceId,
      authorization: wsB.authorization,
    });
    expect(fetched.id).toBe(taskB.id);

    // wsA caller cannot get taskB -> throws 404
    await expect(
      getTask({
        id: taskB.id,
        workspaceId: wsA.workspaceId,
        authorization: wsA.authorization,
      })
    ).rejects.toThrow(/not found/i);
  });

  it("updateTaskStatus: transitions status on valid value, rejects invalid status (400)", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Task Status WS");

    const task = await createTask({
      workspaceId,
      title: "Task to transition",
      authorization,
    });
    expect(task.status).toBe("todo");

    const inProgress = await updateTaskStatus({
      id: task.id,
      status: "in_progress",
      workspaceId,
      authorization,
    });
    expect(inProgress.status).toBe("in_progress");

    // Invalid status string rejected with 400
    await expect(
      updateTaskStatus({
        id: task.id,
        status: "INVALID_STATUS" as any,
        workspaceId,
        authorization,
      })
    ).rejects.toThrow();
  });
});
