import { describe, it, expect } from "vitest";
import { getProjectInWorkspace } from "../services/project-access.service";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { makeTenantContext } from "./tenant-context.fixture";

describe("Project Access Service with Workspace Isolation", () => {
  it("retrieves a project that belongs to the caller's workspace", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Accessible Project",
      description: "Project in caller workspace",
    });

    const ctx = makeTenantContext(ws);
    const retrieved = await getProjectInWorkspace(project.id, ctx);

    expect(retrieved).toBeDefined();
    expect(String(retrieved.id)).toBe(project.id);
    expect(String(retrieved.workspaceId)).toBe(ws.workspaceId);
  });

  it("throws not_found when project does not exist", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = makeTenantContext(ws);

    await expect(getProjectInWorkspace("999999999999999999", ctx)).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("throws not_found when project exists but belongs to a different workspace (fail-closed)", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    // Create project in workspace A
    const projectA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Project in A",
    });

    // Try to access it from workspace B context
    const ctxB = makeTenantContext({ workspaceId: wsB.workspaceId, userId: "fake-user" });

    await expect(getProjectInWorkspace(projectA.id, ctxB)).rejects.toMatchObject({
      code: "not_found",
    });
  });

  it("accepts both string and number project IDs", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "ID Type Test",
    });

    const ctx = makeTenantContext(ws);

    // Test with string
    const fromString = await getProjectInWorkspace(project.id, ctx);
    expect(String(fromString.id)).toBe(project.id);

    // Test with number (parsed from string)
    const projectIdAsNum = Number(project.id);
    const fromNumber = await getProjectInWorkspace(projectIdAsNum, ctx);
    expect(String(fromNumber.id)).toBe(project.id);
  });

  it("returns the full project row with all columns", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Complete Project",
      description: "Test description",
      projectType: "PRODUCT",
      strategicPriority: "P1",
    });

    const ctx = makeTenantContext(ws);
    const retrieved = await getProjectInWorkspace(project.id, ctx);

    expect(retrieved).toBeDefined();
    expect(String(retrieved.workspaceId)).toBe(ws.workspaceId);
    expect(retrieved.title).toBe("Complete Project");
    expect(retrieved.status).toBe("ACTIVE");
  });

  it("works correctly when workspace ID is provided as string or bigint", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Workspace ID Type Test",
    });

    const ctx = makeTenantContext(ws);

    const retrieved = await getProjectInWorkspace(project.id, ctx);
    expect(retrieved).toBeDefined();
    expect(String(retrieved.id)).toBe(project.id);
  });
});
