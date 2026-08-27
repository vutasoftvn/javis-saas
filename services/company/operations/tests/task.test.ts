import { describe, expect, it, vi } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { hireWorkforceMember } from "../../identity/handlers/workforce.handler";
import { createTask, getTask, listTasks, updateTaskStatus, linkTaskProjects_Endpoint, getTaskProjects, unlinkTaskProject_Endpoint } from "../handlers/task.handler";
import { createProject } from "../handlers/project.handler";
import { taskEvents } from "../services/task-events.service";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, userId: user.userId, authorization: `Bearer ${user.accessToken}` };
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
    await expect(createTask({ workspaceId: "999999999", title: "Orphan", authorization })).rejects.toThrow();
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
    const assigneeSession = await createTestSession({ displayName: "Assignee Test Member" });
    const member = await hireWorkforceMember({
      workspaceId,
      memberType: "HUMAN",
      roleTitle: "Ops",
      humanUserId: assigneeSession.userId,
      authorization,
    });

    const task = await createTask({
      workspaceId,
      title: "Assigned task",
      assigneeMemberId: member.id,
      authorization,
    });
    expect(task.assigneeMemberId).toBe(member.id);

    await expect(
      createTask({ workspaceId, title: "Bad assignee", assigneeMemberId: "999999999", authorization })
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
    await expect(getTask({ id: "999999999", authorization })).rejects.toThrow();
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
      updateTaskStatus({ id: "999999999", status: "in_progress", authorization })
    ).rejects.toThrow();
  });
});

describe("linkTaskProjects / getTaskProjects / unlinkTaskProject", () => {
  it("links a task to multiple projects and returns stable IDs", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Task Link Test Inc");
    const task = await createTask({ workspaceId, title: "Multi-project task", authorization });
    const project1 = await createProject({ workspaceId, title: "Project A1", authorization });
    const project2 = await createProject({ workspaceId, title: "Project A2", authorization });

    const response = await linkTaskProjects_Endpoint({
      id: task.id,
      workspaceId,
      authorization,
      projectIds: [project1.id, project2.id],
    });

    expect(response.projectIds).toHaveLength(2);
    expect(response.projectIds).toContain(project1.id);
    expect(response.projectIds).toContain(project2.id);
  });

  it("returns empty projectIds when no links exist", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Task No Links Test");
    const task = await createTask({ workspaceId, title: "Unlinked task", authorization });

    const response = await getTaskProjects({
      id: task.id,
      workspaceId,
      authorization,
    });

    expect(response.projectIds).toEqual([]);
  });

  it("makes duplicate add idempotent", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Task Idempotent Link Test");
    const task = await createTask({ workspaceId, title: "Idempotent link task", authorization });
    const project = await createProject({ workspaceId, title: "Project X", authorization });

    // First link
    await linkTaskProjects_Endpoint({
      id: task.id,
      workspaceId,
      authorization,
      projectIds: [project.id],
    });

    // Second link (should be idempotent)
    const response = await linkTaskProjects_Endpoint({
      id: task.id,
      workspaceId,
      authorization,
      projectIds: [project.id],
    });

    expect(response.projectIds).toHaveLength(1);
    expect(response.projectIds[0]).toBe(project.id);
  });

  it("unlinks a project and leaves others intact", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Task Unlink Test");
    const task = await createTask({ workspaceId, title: "Multi-link task", authorization });
    const project1 = await createProject({ workspaceId, title: "Project 1", authorization });
    const project2 = await createProject({ workspaceId, title: "Project 2", authorization });

    // Link both
    await linkTaskProjects_Endpoint({
      id: task.id,
      workspaceId,
      authorization,
      projectIds: [project1.id, project2.id],
    });

    // Unlink one
    await unlinkTaskProject_Endpoint({
      id: task.id,
      projectId: project1.id,
      workspaceId,
      authorization,
    });

    // Verify only one remains
    const response = await getTaskProjects({
      id: task.id,
      workspaceId,
      authorization,
    });

    expect(response.projectIds).toHaveLength(1);
    expect(response.projectIds[0]).toBe(project2.id);
  });

  it("rejects link to a project in another workspace without disclosing it", async () => {
    const workspace1 = await makeAuthedWorkspace("Task Link W1");
    const workspace2 = await makeAuthedWorkspace("Task Link W2");

    const task = await createTask({
      workspaceId: workspace1.workspaceId,
      title: "Task in W1",
      authorization: workspace1.authorization,
    });

    const projectInW2 = await createProject({
      workspaceId: workspace2.workspaceId,
      title: "Project in W2",
      authorization: workspace2.authorization,
    });

    // Try to link task in W1 to project in W2 — should fail
    await expect(
      linkTaskProjects_Endpoint({
        id: task.id,
        workspaceId: workspace1.workspaceId,
        authorization: workspace1.authorization,
        projectIds: [projectInW2.id],
      })
    ).rejects.toThrow("not found");
  });

  it("populates projectIds on getTask", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Task Fetch Link Test");
    const task = await createTask({ workspaceId, title: "Fetch with links", authorization });
    const project = await createProject({ workspaceId, title: "Project P", authorization });

    // Link
    await linkTaskProjects_Endpoint({
      id: task.id,
      workspaceId,
      authorization,
      projectIds: [project.id],
    });

    // Fetch and verify projectIds is populated
    const fetched = await getTask({ id: task.id, authorization });
    expect(fetched.projectIds).toContain(project.id);
  });
});
