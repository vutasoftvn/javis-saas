import { describe, it, expect } from "vitest";
import {
  linkTaskProjects,
  listTaskProjects,
  unlinkTaskProject,
  linkObjectiveProjects,
  listObjectiveProjects,
  unlinkObjectiveProject,
} from "../services/project-link.service";
import { createProject } from "../handlers/project.handler";
import { createTask } from "../handlers/task.handler";
import { createOkrCycleService, createObjectiveService } from "../services/okr.service";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { makeTenantContext } from "./tenant-context.fixture";

describe("Task-Project Linking Service", () => {
  it("links a task to multiple projects", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Multi-project task",
      authorization: ws.bearerToken,
    });

    const project1 = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project 1",
      authorization: ws.bearerToken,
    });

    const project2 = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project 2",
      authorization: ws.bearerToken,
    });

    await linkTaskProjects(ctx, task.id, [project1.id, project2.id]);

    const projectIds = await listTaskProjects(ctx, task.id);
    expect(projectIds).toHaveLength(2);
    expect(projectIds).toContain(project1.id);
    expect(projectIds).toContain(project2.id);
  });

  it("lists empty array when no projects linked", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Unlinked task",
      authorization: ws.bearerToken,
    });

    const projectIds = await listTaskProjects(ctx, task.id);
    expect(projectIds).toEqual([]);
  });

  it("makes duplicate project links idempotent via onConflictDoNothing", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Idempotent link task",
      authorization: ws.bearerToken,
    });

    const project = await createProject({
      workspaceId: ws.workspaceId,
      title: "Idempotent project",
      authorization: ws.bearerToken,
    });

    // Link the same project twice
    await linkTaskProjects(ctx, task.id, [project.id]);
    await linkTaskProjects(ctx, task.id, [project.id]);

    const projectIds = await listTaskProjects(ctx, task.id);
    expect(projectIds).toHaveLength(1);
    expect(projectIds[0]).toBe(project.id);
  });

  it("unlinks a project and leaves others intact", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Multi-link task",
      authorization: ws.bearerToken,
    });

    const project1 = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project 1",
      authorization: ws.bearerToken,
    });

    const project2 = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project 2",
      authorization: ws.bearerToken,
    });

    // Link both
    await linkTaskProjects(ctx, task.id, [project1.id, project2.id]);

    // Unlink one
    await unlinkTaskProject(ctx, task.id, project1.id);

    // Verify only one remains
    const projectIds = await listTaskProjects(ctx, task.id);
    expect(projectIds).toHaveLength(1);
    expect(projectIds[0]).toBe(project2.id);
  });

  it("treats unlinking a non-existent link as no-op", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "No-op unlink task",
      authorization: ws.bearerToken,
    });

    const project = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project",
      authorization: ws.bearerToken,
    });

    // Unlink a project that was never linked — should not throw
    await expect(unlinkTaskProject(ctx, task.id, project.id)).resolves.toBeUndefined();
  });

  it("throws not_found when task does not exist", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const project = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project",
      authorization: ws.bearerToken,
    });

    await expect(linkTaskProjects(ctx, "999999999999999999", [project.id])).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("throws not_found when listing projects for non-existent task", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    await expect(listTaskProjects(ctx, "999999999999999999")).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("throws not_found when unlinking from non-existent task", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const project = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project",
      authorization: ws.bearerToken,
    });

    await expect(unlinkTaskProject(ctx, "999999999999999999", project.id)).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("throws not_found when linking task to project in different workspace", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember(); // Create second workspace with proper member
    const ctxA = makeTenantContext(wsA);

    const taskA = await createTask({
      workspaceId: wsA.workspaceId,
      title: "Task in A",
      authorization: wsA.bearerToken,
    });

    const projectB = await createProject({
      workspaceId: wsB.workspaceId,
      title: "Project in B",
      authorization: wsB.bearerToken,
    });

    // Try to link task in A to project in B — should fail
    await expect(linkTaskProjects(ctxA, taskA.id, [projectB.id])).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("allows linking empty project list (no-op)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "Empty link task",
      authorization: ws.bearerToken,
    });

    // Link with empty array — should not throw
    await expect(linkTaskProjects(ctx, task.id, [])).resolves.toBeUndefined();

    const projectIds = await listTaskProjects(ctx, task.id);
    expect(projectIds).toEqual([]);
  });

  it("returns projectIds as strings", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const task = await createTask({
      workspaceId: ws.workspaceId,
      title: "String ID task",
      authorization: ws.bearerToken,
    });

    const project = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project",
      authorization: ws.bearerToken,
    });

    await linkTaskProjects(ctx, task.id, [project.id]);
    const projectIds = await listTaskProjects(ctx, task.id);

    expect(projectIds).toHaveLength(1);
    expect(typeof projectIds[0]).toBe("string");
    expect(projectIds[0]).toBe(project.id);
  });
});

describe("Objective-Project Linking Service", () => {
  it("links an objective to multiple projects", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const cycle = await createOkrCycleService({
      workspaceId: ws.workspaceId,
      name: "Q1 2026",
      authorization: ws.bearerToken,
    });

    const objective = await createObjectiveService({
      workspaceId: ws.workspaceId,
      cycleId: cycle.id,
      title: "Multi-project objective",
      authorization: ws.bearerToken,
    });

    const project1 = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project 1",
      authorization: ws.bearerToken,
    });

    const project2 = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project 2",
      authorization: ws.bearerToken,
    });

    await linkObjectiveProjects(ctx, objective.id, [project1.id, project2.id]);

    const projectIds = await listObjectiveProjects(ctx, objective.id);
    expect(projectIds).toHaveLength(2);
    expect(projectIds).toContain(project1.id);
    expect(projectIds).toContain(project2.id);
  });

  it("lists empty array when no projects linked to objective", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const cycle = await createOkrCycleService({
      workspaceId: ws.workspaceId,
      name: "Q1 2026",
      authorization: ws.bearerToken,
    });

    const objective = await createObjectiveService({
      workspaceId: ws.workspaceId,
      cycleId: cycle.id,
      title: "Unlinked objective",
      authorization: ws.bearerToken,
    });

    const projectIds = await listObjectiveProjects(ctx, objective.id);
    expect(projectIds).toEqual([]);
  });

  it("makes duplicate objective-project links idempotent", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const cycle = await createOkrCycleService({
      workspaceId: ws.workspaceId,
      name: "Q1 2026",
      authorization: ws.bearerToken,
    });

    const objective = await createObjectiveService({
      workspaceId: ws.workspaceId,
      cycleId: cycle.id,
      title: "Idempotent link objective",
      authorization: ws.bearerToken,
    });

    const project = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project",
      authorization: ws.bearerToken,
    });

    // Link the same project twice
    await linkObjectiveProjects(ctx, objective.id, [project.id]);
    await linkObjectiveProjects(ctx, objective.id, [project.id]);

    const projectIds = await listObjectiveProjects(ctx, objective.id);
    expect(projectIds).toHaveLength(1);
    expect(projectIds[0]).toBe(project.id);
  });

  it("unlinks a project from objective and leaves others intact", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const cycle = await createOkrCycleService({
      workspaceId: ws.workspaceId,
      name: "Q1 2026",
      authorization: ws.bearerToken,
    });

    const objective = await createObjectiveService({
      workspaceId: ws.workspaceId,
      cycleId: cycle.id,
      title: "Multi-link objective",
      authorization: ws.bearerToken,
    });

    const project1 = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project 1",
      authorization: ws.bearerToken,
    });

    const project2 = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project 2",
      authorization: ws.bearerToken,
    });

    // Link both
    await linkObjectiveProjects(ctx, objective.id, [project1.id, project2.id]);

    // Unlink one
    await unlinkObjectiveProject(ctx, objective.id, project1.id);

    // Verify only one remains
    const projectIds = await listObjectiveProjects(ctx, objective.id);
    expect(projectIds).toHaveLength(1);
    expect(projectIds[0]).toBe(project2.id);
  });

  it("treats unlinking a non-existent objective-project link as no-op", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const cycle = await createOkrCycleService({
      workspaceId: ws.workspaceId,
      name: "Q1 2026",
      authorization: ws.bearerToken,
    });

    const objective = await createObjectiveService({
      workspaceId: ws.workspaceId,
      cycleId: cycle.id,
      title: "No-op unlink objective",
      authorization: ws.bearerToken,
    });

    const project = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project",
      authorization: ws.bearerToken,
    });

    // Unlink a project that was never linked — should not throw
    await expect(unlinkObjectiveProject(ctx, objective.id, project.id)).resolves.toBeUndefined();
  });

  it("throws not_found when objective does not exist", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const project = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project",
      authorization: ws.bearerToken,
    });

    await expect(linkObjectiveProjects(ctx, "999999999999999999", [project.id])).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("throws not_found when listing projects for non-existent objective", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    await expect(listObjectiveProjects(ctx, "999999999999999999")).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("throws not_found when unlinking from non-existent objective", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const project = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project",
      authorization: ws.bearerToken,
    });

    await expect(unlinkObjectiveProject(ctx, "999999999999999999", project.id)).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("throws not_found when linking objective to project in different workspace", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember();
    const ctxA = makeTenantContext(wsA);

    const cycle = await createOkrCycleService({
      workspaceId: wsA.workspaceId,
      name: "Q1 2026",
      authorization: wsA.bearerToken,
    });

    const objectiveA = await createObjectiveService({
      workspaceId: wsA.workspaceId,
      cycleId: cycle.id,
      title: "Objective in A",
      authorization: wsA.bearerToken,
    });

    const projectB = await createProject({
      workspaceId: wsB.workspaceId,
      title: "Project in B",
      authorization: wsB.bearerToken,
    });

    // Try to link objective in A to project in B — should fail
    await expect(linkObjectiveProjects(ctxA, objectiveA.id, [projectB.id])).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("allows linking empty project list to objective (no-op)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const cycle = await createOkrCycleService({
      workspaceId: ws.workspaceId,
      name: "Q1 2026",
      authorization: ws.bearerToken,
    });

    const objective = await createObjectiveService({
      workspaceId: ws.workspaceId,
      cycleId: cycle.id,
      title: "Empty link objective",
      authorization: ws.bearerToken,
    });

    // Link with empty array — should not throw
    await expect(linkObjectiveProjects(ctx, objective.id, [])).resolves.toBeUndefined();

    const projectIds = await listObjectiveProjects(ctx, objective.id);
    expect(projectIds).toEqual([]);
  });

  it("returns objective projectIds as strings", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    const cycle = await createOkrCycleService({
      workspaceId: ws.workspaceId,
      name: "Q1 2026",
      authorization: ws.bearerToken,
    });

    const objective = await createObjectiveService({
      workspaceId: ws.workspaceId,
      cycleId: cycle.id,
      title: "String ID objective",
      authorization: ws.bearerToken,
    });

    const project = await createProject({
      workspaceId: ws.workspaceId,
      title: "Project",
      authorization: ws.bearerToken,
    });

    await linkObjectiveProjects(ctx, objective.id, [project.id]);
    const projectIds = await listObjectiveProjects(ctx, objective.id);

    expect(projectIds).toHaveLength(1);
    expect(typeof projectIds[0]).toBe("string");
    expect(projectIds[0]).toBe(project.id);
  });
});
