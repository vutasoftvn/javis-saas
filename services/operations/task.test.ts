import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createOrganization, hireWorkforceMember } from "../identity/organization";
import { createTask, getTask, listTasks, updateTaskStatus } from "./task";

async function makeWorkspace(name: string) {
  return createWorkspace({ name });
}

describe("createTask", () => {
  it("creates a task with canonical defaults", async () => {
    const workspace = await makeWorkspace("Task Test Inc");
    const task = await createTask({ workspaceId: workspace.id, title: "Write plan" });
    expect(task.id).toBeGreaterThan(0);
    expect(task.workspaceId).toBe(workspace.id);
    expect(task.status).toBe("todo");
    expect(task.priority).toBe("medium");
    expect(task.timezone).toBe("UTC");
  });

  it("rejects a task for a workspace that doesn't exist", async () => {
    await expect(createTask({ workspaceId: 999999999, title: "Orphan" })).rejects.toThrow();
  });

  it("validates assigneeMemberId against identity when provided", async () => {
    const workspace = await makeWorkspace("Assignee Test Inc");
    const org = await createOrganization({ workspaceId: workspace.id, name: "Assignee Test Inc" });
    const member = await hireWorkforceMember({ organizationId: org.id, memberType: "HUMAN", roleTitle: "Ops" });

    const task = await createTask({
      workspaceId: workspace.id,
      title: "Assigned task",
      assigneeMemberId: member.id,
    });
    expect(task.assigneeMemberId).toBe(member.id);

    await expect(
      createTask({ workspaceId: workspace.id, title: "Bad assignee", assigneeMemberId: 999999999 })
    ).rejects.toThrow();
  });

  it("returns the original task instead of creating a duplicate for a repeated idempotencyKey", async () => {
    const workspace = await makeWorkspace("Idempotency Test Inc");

    const first = await createTask({
      workspaceId: workspace.id,
      title: "Send weekly report",
      idempotencyKey: "agent-run-42",
    });
    const retried = await createTask({
      workspaceId: workspace.id,
      title: "Send weekly report (retry)",
      idempotencyKey: "agent-run-42",
    });

    expect(retried.id).toBe(first.id);
    expect(retried.title).toBe("Send weekly report");

    const { tasks } = await listTasks({ workspaceId: workspace.id });
    expect(tasks.filter((t) => t.idempotencyKey === "agent-run-42")).toHaveLength(1);
  });

  it("allows multiple tasks with no idempotencyKey (NULLs don't conflict)", async () => {
    const workspace = await makeWorkspace("No Key Test Inc");

    const first = await createTask({ workspaceId: workspace.id, title: "Task A" });
    const second = await createTask({ workspaceId: workspace.id, title: "Task B" });

    expect(first.id).not.toBe(second.id);
  });
});

describe("getTask/listTasks", () => {
  it("fetches a created task and lists it by workspace", async () => {
    const workspace = await makeWorkspace("List Test Inc");
    const created = await createTask({ workspaceId: workspace.id, title: "Fetch me" });

    const fetched = await getTask({ id: created.id });
    expect(fetched).toEqual(created);

    const { tasks } = await listTasks({ workspaceId: workspace.id });
    expect(tasks.map((t) => t.id)).toContain(created.id);
  });

  it("throws not found for a missing id", async () => {
    await expect(getTask({ id: 999999999 })).rejects.toThrow();
  });
});

describe("updateTaskStatus", () => {
  it("transitions through the canonical status vocabulary and publishes on done", async () => {
    const workspace = await makeWorkspace("Status Test Inc");
    const created = await createTask({ workspaceId: workspace.id, title: "Ship it" });

    const inProgress = await updateTaskStatus({ id: created.id, status: "in_progress" });
    expect(inProgress.status).toBe("in_progress");

    const done = await updateTaskStatus({ id: created.id, status: "done" });
    expect(done.status).toBe("done");
  });

  it("rejects a status outside the canonical vocabulary", async () => {
    const workspace = await makeWorkspace("Bad Status Test Inc");
    const created = await createTask({ workspaceId: workspace.id, title: "Bad status" });
    await expect(updateTaskStatus({ id: created.id, status: "completed" as any })).rejects.toThrow();
  });
});
