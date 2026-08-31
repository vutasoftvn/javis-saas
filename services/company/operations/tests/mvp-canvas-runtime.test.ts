import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { hireWorkforceMember } from "../../identity/handlers/workforce.handler";
import { createTask, updateTaskStatus } from "../handlers/task.handler";
import { createTaskDependency } from "../handlers/task-dependency.handler";
import {
  listCanvases,
  createCanvas,
  getCanvas,
  updateCanvas,
  deleteCanvas,
  createRevision,
  getRevision,
  submitRevisionForReview,
  approveRevision,
  rejectRevision,
} from "../handlers/canvas.handler";
import {
  listNeedsYou,
  listBlockers,
  getWorkInspector,
  snoozeRuntimeItem,
  getSourceStatus,
} from "../handlers/workspace-runtime.handler";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("Strategy Canvas & Workspace Runtime API", () => {
  it("returns empty canvases only after an authorized query", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Canvas List Test");
    const res = await listCanvases({ workspaceId, authorization });
    expect(res.meta.dataState).toBe("empty");
    expect(res.data).toEqual([]);
    expect(res.meta.sources[0]).toMatchObject({ kind: "company_db", ref: "strategy.canvases" });
  });

  it("creates, reads, updates and deletes a canvas", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Canvas CRUD Test");
    const created = await createCanvas({
      workspaceId,
      authorization,
      name: "Lean Canvas 1",
      description: "Initial business model",
    });

    expect(created.data.id).toBeTruthy();
    expect(created.data.name).toBe("Lean Canvas 1");
    expect(created.meta.dataState).toBe("populated");

    const fetched = await getCanvas({ workspaceId, authorization, id: created.data.id });
    expect(fetched.data.name).toBe("Lean Canvas 1");

    const updated = await updateCanvas({
      workspaceId,
      authorization,
      id: created.data.id,
      name: "Lean Canvas v2",
    });
    expect(updated.data.name).toBe("Lean Canvas v2");

    await deleteCanvas({ workspaceId, authorization, id: created.data.id });
    await expect(getCanvas({ workspaceId, authorization, id: created.data.id })).rejects.toThrow();
  });

  it("handles revision lifecycle with status transitions", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Canvas Revisions Test");
    const canvas = await createCanvas({
      workspaceId,
      authorization,
      name: "Strategy Canvas",
    });

    // 1. User draft
    const rev1 = await createRevision({
      workspaceId,
      authorization,
      id: canvas.data.id,
      content: { problem: "Customer pain point", solution: "Automated solution" },
      origin: "USER",
    });
    expect(rev1.data.status).toBe("DRAFT");
    expect(rev1.data.origin).toBe("USER");

    // 2. Submit for review
    const inReview = await submitRevisionForReview({
      workspaceId,
      authorization,
      id: rev1.data.id,
    });
    expect(inReview.data.status).toBe("IN_REVIEW");

    // 3. Approve revision -> sets canvas currentRevisionId
    const approved = await approveRevision({
      workspaceId,
      authorization,
      id: rev1.data.id,
      reviewNote: "Looks solid",
    });
    expect(approved.data.status).toBe("APPROVED");
    expect(approved.data.reviewNote).toBe("Looks solid");

    const refreshedCanvas = await getCanvas({ workspaceId, authorization, id: canvas.data.id });
    expect(refreshedCanvas.data.currentRevisionId).toBe(rev1.data.id);
  });

  it("does not accept a model draft without source refs", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Model Draft Test");
    const canvas = await createCanvas({ workspaceId, authorization, name: "AI Draft Canvas" });

    await expect(
      createRevision({
        workspaceId,
        authorization,
        id: canvas.data.id,
        content: { generated: true },
        origin: "MODEL_DRAFT",
        sourceRefs: [],
      })
    ).rejects.toThrow();
  });

  it("accepts a model draft with valid source refs", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Model Draft Valid Test");
    const canvas = await createCanvas({ workspaceId, authorization, name: "AI Draft Canvas 2" });

    const rev = await createRevision({
      workspaceId,
      authorization,
      id: canvas.data.id,
      content: { generated: true },
      origin: "MODEL_DRAFT",
      sourceRefs: [{ kind: "company_db", ref: "operating.assumptions:1" }],
    });
    expect(rev.data.origin).toBe("MODEL_DRAFT");
    expect(rev.data.status).toBe("DRAFT");
  });

  it("workspace runtime lists needs-you and blockers honestly", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Workspace Runtime Test");
    const needsYou = await listNeedsYou({ workspaceId, authorization });
    expect(needsYou.meta.dataState).toBe("empty");
    expect(needsYou.data).toEqual([]);

    const blockers = await listBlockers({ workspaceId, authorization });
    expect(blockers.meta.dataState).toBe("empty");
    expect(blockers.data).toEqual([]);

    const status = await getSourceStatus({ workspaceId, authorization });
    expect(status.data.length).toBeGreaterThan(0);
    expect(["HEALTHY", "NOT_OBSERVED"]).toContain(status.data[0].status);
  });

  it("projects canonical task states, priorities, and unresolved prerequisites", async () => {
    const session = await createTestSession({
      email: `runtime-projection-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
      displayName: "Runtime Projection Test",
    });
    const workspaceId = session.workspaceId;
    const authorization = `Bearer ${session.accessToken}`;
    const member = await hireWorkforceMember({
      workspaceId,
      memberType: "HUMAN",
      roleTitle: "Operations",
      humanUserId: session.userId,
      authorization,
    });

    const todo = await createTask({
      workspaceId,
      authorization,
      title: "Prepare launch brief",
      priority: "medium",
      assigneeMemberId: member.id,
    });
    const inProgress = await createTask({
      workspaceId,
      authorization,
      title: "Approve supplier contract",
      priority: "high",
      assigneeMemberId: member.id,
    });
    await updateTaskStatus({ id: inProgress.id, status: "in_progress", workspaceId, authorization });

    const waitingApproval = await createTask({
      workspaceId,
      authorization,
      title: "Review pricing exception",
      priority: "urgent",
      assigneeMemberId: member.id,
    });
    await updateTaskStatus({ id: waitingApproval.id, status: "waiting_approval", workspaceId, authorization });

    const needsYou = await listNeedsYou({ workspaceId, authorization });
    const needsYouByTitle = new Map(needsYou.data.map((item) => [item.title, item]));
    expect(needsYouByTitle.get(todo.title)).toMatchObject({ state: "todo", severity: "MEDIUM" });
    expect(needsYouByTitle.get(inProgress.title)).toMatchObject({ state: "in_progress", severity: "HIGH" });
    expect(needsYouByTitle.get(waitingApproval.title)).toMatchObject({ state: "waiting_approval", severity: "HIGH" });

    const prerequisite = await createTask({ workspaceId, authorization, title: "Provision production database" });
    const dependent = await createTask({ workspaceId, authorization, title: "Deploy application" });
    await createTaskDependency({
      workspaceId,
      authorization,
      taskId: dependent.id,
      dependsOnTaskId: prerequisite.id,
    });

    let blockers = await listBlockers({ workspaceId, authorization });
    expect(blockers.data).toEqual(
      expect.arrayContaining([expect.objectContaining({ sourceId: dependent.id, title: `Blocked Task: ${dependent.title}` })])
    );

    await updateTaskStatus({ id: prerequisite.id, status: "done", workspaceId, authorization });
    blockers = await listBlockers({ workspaceId, authorization });
    expect(blockers.data).not.toEqual(expect.arrayContaining([expect.objectContaining({ sourceId: dependent.id })]));
  });
});
