import { describe, it, expect } from "vitest";
import { makeTenantContext } from "./tenant-context.fixture";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { createProject } from "../handlers/project.handler";
import {
  createDiscoverySignalInWorkspace,
  getDiscoverySignalInWorkspace,
  listDiscoverySignalsInWorkspace,
  updateDiscoverySignalInWorkspace,
  deleteDiscoverySignalInWorkspace,
} from "../strategy/services/discovery-signal.service";

describe("Discovery Signal Service", () => {
  it("creates, queries, and protects discovery signals by workspace", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    const projectA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Project A",
    });

    const ctxA = makeTenantContext(wsA);
    const ctxB = makeTenantContext({ workspaceId: wsB.workspaceId, userId: wsA.userId });

    const signal = await createDiscoverySignalInWorkspace(ctxA, {
      projectId: projectA.id,
      signalType: "market_trend",
      source: "competitor_analysis",
      payload: { market: "saas", growth: 25 },
    });

    expect(signal.id).toBeDefined();
    expect(signal.workspaceId).toBe(wsA.workspaceId);
    expect(signal.signalType).toBe("market_trend");

    // Same workspace lookup
    const found = await getDiscoverySignalInWorkspace(ctxA, signal.id);
    expect(found.id).toBe(signal.id);

    // Cross workspace lookup throws not_found
    await expect(getDiscoverySignalInWorkspace(ctxB, signal.id)).rejects.toMatchObject({
      code: "not_found",
    });

    // List in workspace
    const listA = await listDiscoverySignalsInWorkspace(ctxA, { projectId: projectA.id });
    expect(listA.items.some((i) => i.id === signal.id)).toBe(true);

    const listB = await listDiscoverySignalsInWorkspace(ctxB, {});
    expect(listB.items.some((i) => i.id === signal.id)).toBe(false);

    // Update
    const updated = await updateDiscoverySignalInWorkspace(ctxA, signal.id, {
      source: "updated_analysis",
    });
    expect(updated.source).toBe("updated_analysis");

    // Delete
    await deleteDiscoverySignalInWorkspace(ctxA, signal.id);
    await expect(getDiscoverySignalInWorkspace(ctxA, signal.id)).rejects.toMatchObject({
      code: "not_found",
    });
  });
});
