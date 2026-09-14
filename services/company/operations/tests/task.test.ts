import { describe, expect, it, vi } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { hireWorkforceMember } from "../../identity/handlers/workforce.handler";
import { createTask, getTask, listTasks, updateTaskStatus, updateTaskSchedule } from "../handlers/task.handler";
import { readOutbox } from "./helpers/outbox";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  const authorization = `Bearer ${user.accessToken}`;
  // Startup Core: createTestSession seed sẵn một project (id === workspaceId).
  return { workspaceId: user.workspaceId, userId: user.userId, authorization, projectId: user.projectId };
}

describe("createTask", () => {
  it("creates a task with canonical defaults", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Task Test Inc");
    const task = await createTask({ workspaceId, projectId: workspaceId, title: "Write plan", authorization });
    expect(task.id).toBeTruthy();
    expect(typeof task.id).toBe("string");
    expect(task.workspaceId).toBe(workspaceId);
    expect(task.status).toBe("todo");
    expect(task.priority).toBe("medium");
    expect(task.timezone).toBe("UTC");
  });

  it("rejects a task for a workspace that doesn't exist", async () => {
    const { authorization } = await makeAuthedWorkspace("Nonexistent Ws Task Test");
    await expect(createTask({ workspaceId: "999999999",
      projectId: "999999999", title: "Orphan", authorization })).rejects.toThrow();
  });

  it("rejects when caller is not a member of the target workspace", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Owner Task Ws");
    const outsider = await makeAuthedWorkspace("Outsider Task Test");
    await expect(
      createTask({ workspaceId, projectId: workspaceId, title: "Should be blocked", authorization: outsider.authorization })
    ).rejects.toThrow();
  });

  it("validates assigneeMemberId against identity when provided", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Assignee Test Inc");
    const assigneeSession = await createTestSession({ displayName: "Assignee Test Member" });
    const member = await hireWorkforceMember({
      workspaceId,
      memberType: "HUMAN",
      roleTitle: "Ops",
      humanUserId: assigneeSession.userId,
      authorization,
    });

    const task = await createTask({ workspaceId, projectId: workspaceId,
      title: "Assigned task",
      assigneeMemberId: member.id,
      authorization,
    });
    expect(task.assigneeMemberId).toBe(member.id);

    await expect(
      createTask({ workspaceId, projectId: workspaceId, title: "Bad assignee", assigneeMemberId: "999999999", authorization })
    ).rejects.toThrow();
  });

  it("returns the original task instead of creating a duplicate for a repeated idempotencyKey", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Idempotency Test Inc");

    const first = await createTask({ workspaceId, projectId: workspaceId,
      title: "Send weekly report",
      idempotencyKey: "agent-run-42",
      authorization,
    });
    const retried = await createTask({ workspaceId, projectId: workspaceId,
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

    const first = await createTask({ workspaceId, projectId: workspaceId, title: "Task A", authorization });
    const second = await createTask({ workspaceId, projectId: workspaceId, title: "Task B", authorization });

    expect(first.id).not.toBe(second.id);
  });

  it("appends one canonical operations.task.created.v1 outbox event on genuine insert", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Created Event Test Inc");
    const task = await createTask({ workspaceId, projectId: workspaceId, title: "Notify on create", authorization });

    const rows = await readOutbox(workspaceId, "task", task.id);
    expect(rows).toHaveLength(1);
    expect(rows[0].eventType).toBe("operations.task.created.v1");
    expect(rows[0].envelope).toMatchObject({
      schemaVersion: 1,
      workspaceId,
      aggregateId: task.id,
      payload: { taskId: task.id, workspaceId, title: "Notify on create", status: "todo" },
    });
    expect(rows[0].envelope.eventId).toMatch(/^[0-9a-f-]{36}$/);
    expect(rows[0].envelope.correlationId).toBeTruthy();
  });

  it("does not re-publish task.created when an idempotencyKey retry returns the existing row", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Idempotent Event Test Inc");
    const first = await createTask({ workspaceId, projectId: workspaceId, title: "First", idempotencyKey: "agent-run-99", authorization });
    const rowsFirst = await readOutbox(workspaceId, "task", first.id);
    expect(rowsFirst).toHaveLength(1);

    await createTask({ workspaceId, projectId: workspaceId, title: "Retry", idempotencyKey: "agent-run-99", authorization });
    const rowsSecond = await readOutbox(workspaceId, "task", first.id);
    expect(rowsSecond).toHaveLength(1);
  });
});

describe("getTask/listTasks", () => {
  it("fetches a created task and lists it by workspace", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("List Test Inc");
    const created = await createTask({ workspaceId, projectId: workspaceId, title: "Fetch me", authorization });

    const fetched = await getTask({ id: created.id, workspaceId, authorization });
    expect(fetched).toEqual(created);

    const { tasks } = await listTasks({ workspaceId, authorization });
    expect(tasks.map((t) => t.id)).toContain(created.id);
  });

  it("throws not found for a missing id", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Missing Task Test");
    await expect(getTask({ id: "999999999", workspaceId, authorization })).rejects.toThrow();
  });

  it("does not allow a workspace B member to read a task from workspace A (404, not 403)", async () => {
    const workspaceA = await makeAuthedWorkspace("Task Isolation Ws A");
    const workspaceB = await makeAuthedWorkspace("Task Isolation Ws B");
    const taskA = await createTask({
      workspaceId: workspaceA.workspaceId,
      projectId: workspaceA.workspaceId,
      title: "Secret task in A",
      authorization: workspaceA.authorization,
    });

    await expect(
      getTask({ id: taskA.id, workspaceId: workspaceB.workspaceId, authorization: workspaceB.authorization })
    ).rejects.toThrow(/not found/i);
  });
});

describe("updateTaskStatus", () => {
  it("transitions through the canonical status vocabulary and publishes on done", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Status Test Inc");
    const created = await createTask({ workspaceId, projectId: workspaceId, title: "Ship it", authorization });

    const inProgress = await updateTaskStatus({ id: created.id, status: "in_progress", workspaceId, authorization });
    expect(inProgress.status).toBe("in_progress");
    let rows = await readOutbox(workspaceId, "task", created.id);
    expect(rows.filter((r) => r.eventType === "operations.task.completed.v1")).toHaveLength(0);

    const done = await updateTaskStatus({ id: created.id, status: "done", workspaceId, authorization });
    expect(done.status).toBe("done");
    rows = await readOutbox(workspaceId, "task", created.id);
    const completedRow = rows.find((r) => r.eventType === "operations.task.completed.v1");
    expect(completedRow).toBeDefined();
    expect(completedRow?.envelope).toMatchObject({
      schemaVersion: 1,
      workspaceId,
      aggregateId: created.id,
      payload: { taskId: created.id, workspaceId },
    });
  });

  it("rejects a status outside the canonical vocabulary", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Bad Status Test Inc");
    const created = await createTask({ workspaceId, projectId: workspaceId, title: "Bad status", authorization });
    await expect(
      updateTaskStatus({ id: created.id, status: "completed" as any, workspaceId, authorization })
    ).rejects.toThrow();
  });

  it("throws not found for a missing id", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Missing Task Status Test");
    await expect(
      updateTaskStatus({ id: "999999999", status: "in_progress", workspaceId, authorization })
    ).rejects.toThrow();
  });

  it("does not allow a workspace B member to update a task from workspace A (404, not 403)", async () => {
    const workspaceA = await makeAuthedWorkspace("Task Status Isolation Ws A");
    const workspaceB = await makeAuthedWorkspace("Task Status Isolation Ws B");
    const taskA = await createTask({
      workspaceId: workspaceA.workspaceId,
      projectId: workspaceA.workspaceId,
      title: "Task in A",
      authorization: workspaceA.authorization,
    });

    await expect(
      updateTaskStatus({
        id: taskA.id,
        status: "in_progress",
        workspaceId: workspaceB.workspaceId,
        authorization: workspaceB.authorization,
      })
    ).rejects.toThrow(/not found/i);
  });
});

describe("updateTaskSchedule", () => {
  it("sets plannedStartAt from an ISO string", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Schedule Test Inc");
    const created = await createTask({ workspaceId, projectId: workspaceId, title: "Interview lead", authorization });
    expect(created.plannedStartAt).toBeNull();

    const scheduled = await updateTaskSchedule({
      id: created.id,
      plannedStartAt: "2026-09-08T09:00:00.000Z",
      workspaceId,
      authorization,
    });

    expect(scheduled.plannedStartAt).toBe("2026-09-08T09:00:00.000Z");
  });

  it("clears plannedStartAt when null is passed", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Schedule Clear Test Inc");
    const created = await createTask({ workspaceId, projectId: workspaceId, title: "Interview lead", authorization });
    await updateTaskSchedule({
      id: created.id,
      plannedStartAt: "2026-09-08T09:00:00.000Z",
      workspaceId,
      authorization,
    });

    const cleared = await updateTaskSchedule({
      id: created.id,
      plannedStartAt: null,
      workspaceId,
      authorization,
    });

    expect(cleared.plannedStartAt).toBeNull();
  });

  it("rejects an invalid (non-ISO) plannedStartAt string", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Schedule Bad Date Test Inc");
    const created = await createTask({ workspaceId, projectId: workspaceId, title: "Interview lead", authorization });

    await expect(
      updateTaskSchedule({ id: created.id, plannedStartAt: "not-a-date", workspaceId, authorization })
    ).rejects.toThrow();
  });

  it("throws not found for a missing id", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Missing Task Schedule Test");
    await expect(
      updateTaskSchedule({ id: "999999999", plannedStartAt: null, workspaceId, authorization })
    ).rejects.toThrow();
  });

  it("does not allow a workspace B member to schedule a task from workspace A (404, not 403)", async () => {
    const workspaceA = await makeAuthedWorkspace("Task Schedule Isolation Ws A");
    const workspaceB = await makeAuthedWorkspace("Task Schedule Isolation Ws B");
    const taskA = await createTask({
      workspaceId: workspaceA.workspaceId,
      projectId: workspaceA.workspaceId,
      title: "Task in A",
      authorization: workspaceA.authorization,
    });

    await expect(
      updateTaskSchedule({
        id: taskA.id,
        plannedStartAt: "2026-09-08T09:00:00.000Z",
        workspaceId: workspaceB.workspaceId,
        authorization: workspaceB.authorization,
      })
    ).rejects.toThrow(/not found/i);
  });
});

describe("task ↔ project (direct column)", () => {
  it("populates projectId / projectIds on getTask from tasks.project_id", async () => {
    const { workspaceId, authorization, projectId } = await makeAuthedWorkspace("Task Fetch Link Test");
    // Startup Core: task thuộc đúng một project qua cột `tasks.project_id` —
    // createTask với projectId tường minh, không còn M:N link.
    const task = await createTask({ workspaceId, title: "Fetch with project", authorization, projectId });

    const fetched = await getTask({ id: task.id, workspaceId, authorization });
    expect(fetched.projectId).toBe(projectId);
    expect(fetched.projectIds).toEqual([projectId]);
  });
});
