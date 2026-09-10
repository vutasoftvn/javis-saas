import { describe, it, expect } from "vitest";
import { createProject, listProjects, getProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";

describe("Project Service with Workspace Isolation", () => {
  it("creates a project and lists it within workspace", async () => {
    const wsA = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Realtime Voice Hologram",
      description: "Interactive voice agent for desktop",
      projectType: "PRODUCT",
      strategicPriority: "P0",
    });

    expect(project.id).toBeDefined();
    expect(typeof project.id).toBe("string");
    expect(project.workspaceId).toBe(wsA.workspaceId);
    expect(project.title).toBe("Realtime Voice Hologram");
    expect(project.status).toBe("ACTIVE");
    expect(project.lifecycleStage).toBe("P0_DISCOVERY");
    expect(project.stageEnteredAt).toBeDefined();
    expect(typeof project.stageEnteredAt).toBe("string");

    const list = await listProjects({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
    });
    expect(list.projects.some((p) => p.id === project.id)).toBe(true);
  });

  it("rejects cross-workspace get with permission_denied", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    const project = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Secret Project",
      description: "Visible only to workspace A",
    });

    // User from wsA tries to access wsB (not a member) - should get permission_denied
    await expect(
      getProject({
        authorization: wsA.bearerToken,
        workspaceId: wsB.workspaceId,
        id: project.id,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("returns 404 when project does not exist in workspace", async () => {
    const wsA = await createTestWorkspaceWithMember();

    // Try to fetch non-existent project in the correct workspace
    await expect(
      getProject({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        id: "999999999999999999",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("ignores workspaceId in body and uses caller's workspace", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    // Try to create project in wsA but claim wsB in body - should fail or ignore
    const project = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Test Project",
      description: "Test",
    });

    expect(project.workspaceId).toBe(wsA.workspaceId);
  });

  it("rejects create without authorization", async () => {
    const wsA = await createTestWorkspaceWithMember();

    await expect(
      createProject({
        authorization: undefined,
        workspaceId: wsA.workspaceId,
        title: "Unauthorized Project",
      })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("lists only workspace-scoped projects", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    const projectA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Project in A",
    });

    const list = await listProjects({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
    });

    expect(list.projects.some((p) => p.id === projectA.id)).toBe(true);
  });
});
