import { describe, expect, it, vi } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { hireWorkforceMember } from "../../identity/handlers/workforce.handler";
import { createTask, getTask, listTasks, updateTaskStatus } from "../handlers/task.handler";
import { taskEvents } from "../services/task-events.service";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("createTask", () => {
  it("creates a task with canonical defaults", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Task Test Inc");
    const task = await createTask({ workspaceId, title: "Write plan", authorization });
    expect(task.id).toBeTruthy();
    expect(typeof task.id).toBe("string");
    expect(task.workspaceId).toBe(workspaceId);
    expect(task.status).toBe("todo");
    expect(task.priority).toBe("medium");
    expect(task.timezone).toBe("UTC");
  });

  it("rejects a task for a workspace that doesn't exist", async () => {
    const { authorization } = await makeAuthedWorkspace("Nonexistent Ws Task Test");
    await expect(createTask({ workspaceId: 999999999, title: "Orphan", authorization })).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Task Ws");
    const outsider = await makeAuthedWorkspace("Outsider Task Test");
    await expect(
      createTask({ workspaceId, title: "Should be blocked", authorization: outsider.authorization })
    ).rejects.toThrow();
  });

  it("validates assigneeMemberId against identity when provided", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Assignee Test Inc");
    const member = await hireWorkforceMember({ workspaceId, memberType: "HUMAN", roleTitle: "Ops" });

    const task = await createTask({
      workspaceId,
      title: "Assigned task",
      assigneeMemberId: member.id,
      authorization,
    });
    expect(task.assigneeMemberId).toBe(member.id);

    await expect(
      createTask({ workspaceId, title: "Bad assignee", assigneeMemberId: 999999999, authorization })
    ).rejects.toThrow();
  });

  it("returns the original task instead of creating a duplicate for a repeated idempotencyKey", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Idempotency Test Inc");

    const first = await createTask({
      workspaceId,
      title: "Send weekly report",
      idempotencyKey: "agent-run-42",
      authorization,
    });
    const retried = await createTask({
      workspaceId,
      title: "Send weekly report (retry)",
      idempotencyKey: "agent-run-42",
      authorization,
    });

    expect(retried.id).toBe(first.id);
    expect(retried.title).toBe("Send weekly report");

    const { tasks } = await listTasks({ workspaceId, authorization });
    expect(tasks.filter((t) => t.idempotencyKey === "agent-run-42")).toHaveLength(1);
  });

  it("allows multiple tasks with no idempotencyKey (NULLs don't conflict)", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("No Key Test Inc");

    const first = await createTask({ workspaceId, title: "Task A", authorization });
    const second = await createTask({ workspaceId, title: "Task B", authorization });

    expect(first.id).not.toBe(second.id);
  });

  it("publishes task.created on a genuine insert", async () => {
    const publishSpy = vi.spyOn(taskEvents, "publish").mockResolvedValue("test-message-id");
    try {
      const { workspaceId, authorization } = await makeAuthedWorkspace("Created Event Test Inc");
      const task = await createTask({ workspaceId, title: "Notify on create", authorization });

      expect(publishSpy).toHaveBeenCalledTimes(1);
      expect(publishSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "task.created",
          payload: { taskId: task.id, workspaceId },
        })
      );
    } finally {
      publishSpy.mockRestore();
    }
  });

  it("does not re-publish task.created when an idempotencyKey retry returns the existing row", async () => {
    const publishSpy = vi.spyOn(taskEvents, "publish").mockResolvedValue("test-message-id");
    try {
      const { workspaceId, authorization } = await makeAuthedWorkspace("Idempotent Event Test Inc");
      await createTask({ workspaceId, title: "First", idempotencyKey: "agent-run-99", authorization });
      expect(publishSpy).toHaveBeenCalledTimes(1);

      await createTask({ workspaceId, title: "Retry", idempotencyKey: "agent-run-99", authorization });
      expect(publishSpy).toHaveBeenCalledTimes(1);
    } finally {
      publishSpy.mockRestore();
    }
  });
});

describe("getTask/listTasks", () => {
  it("fetches a created task and lists it by workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("List Test Inc");
    const created = await createTask({ workspaceId, title: "Fetch me", authorization });

    const fetched = await getTask({ id: created.id, authorization });
    expect(fetched).toEqual(created);

    const { tasks } = await listTasks({ workspaceId, authorization });
    expect(tasks.map((t) => t.id)).toContain(created.id);
  });

  it("throws not found for a missing id", async () => {
    const { authorization } = await makeAuthedWorkspace("Missing Task Test");
    await expect(getTask({ id: 999999999, authorization })).rejects.toThrow();
  });
});

describe("updateTaskStatus", () => {
  it("transitions through the canonical status vocabulary and publishes on done", async () => {
    const publishSpy = vi.spyOn(taskEvents, "publish").mockResolvedValue("test-message-id");
    try {
      const { workspaceId, authorization } = await makeAuthedWorkspace("Status Test Inc");
      const created = await createTask({ workspaceId, title: "Ship it", authorization });
      publishSpy.mockClear(); // createTask itself publishes task.created — not what this test checks

      const inProgress = await updateTaskStatus({ id: created.id, status: "in_progress", authorization });
      expect(inProgress.status).toBe("in_progress");
      expect(publishSpy).not.toHaveBeenCalled();

      const done = await updateTaskStatus({ id: created.id, status: "done", authorization });
      expect(done.status).toBe("done");
      expect(publishSpy).toHaveBeenCalledTimes(1);
      expect(publishSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          payload: { taskId: created.id, workspaceId },
        })
      );
    } finally {
      publishSpy.mockRestore();
    }
  });

  it("rejects a status outside the canonical vocabulary", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Bad Status Test Inc");
    const created = await createTask({ workspaceId, title: "Bad status", authorization });
    await expect(
      updateTaskStatus({ id: created.id, status: "completed" as any, authorization })
    ).rejects.toThrow();
  });

  it("throws not found for a missing id", async () => {
    const { authorization } = await makeAuthedWorkspace("Missing Task Status Test");
    await expect(
      updateTaskStatus({ id: 999999999, status: "in_progress", authorization })
    ).rejects.toThrow();
  });
});
