import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  listFounderAssetLibraryApi,
  getProjectFounderDeploymentsApi,
  getProjectAgentTimelineApi,
} from "../handlers/founder-asset-query.handler";

describe("Founder Asset Query Handler", () => {
  it("rejects unauthenticated requests", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    await expect(
      listFounderAssetLibraryApi({ authorization: undefined, workspaceId: ws.workspaceId })
    ).rejects.toThrow(/unauthenticated|authorization|token/i);
    await expect(
      getProjectFounderDeploymentsApi({
        authorization: undefined,
        workspaceId: ws.workspaceId,
        projectId: ws.projectId,
      })
    ).rejects.toThrow(/unauthenticated|authorization|token/i);
    await expect(
      getProjectAgentTimelineApi({
        authorization: undefined,
        workspaceId: ws.workspaceId,
        projectId: ws.projectId,
      })
    ).rejects.toThrow(/unauthenticated|authorization|token/i);
  });

  it("rejects a plain member with no founder/co-founder authority", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    await expect(
      listFounderAssetLibraryApi({ authorization: ws.bearerToken, workspaceId: ws.workspaceId })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("returns an empty library for a fresh workspace (founder access)", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const result = await listFounderAssetLibraryApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
    });
    expect(result.data).toEqual([]);
  });

  it("returns empty deployments/timeline for a fresh project (founder access)", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const deployments = await getProjectFounderDeploymentsApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
    });
    expect(deployments.data).toEqual({ roles: [], agents: [], workflows: [] });

    const timeline = await getProjectAgentTimelineApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
    });
    expect(timeline.data).toEqual([]);
  });

  it("returns indistinguishable 404 for a project belonging to another workspace", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "founder" });
    const wsB = await createTestWorkspaceWithMember({ role: "founder" });

    await expect(
      getProjectFounderDeploymentsApi({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        projectId: wsB.projectId,
      })
    ).rejects.toThrow(/not found/i);

    await expect(
      getProjectAgentTimelineApi({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        projectId: wsB.projectId,
      })
    ).rejects.toThrow(/not found/i);
  });
});
