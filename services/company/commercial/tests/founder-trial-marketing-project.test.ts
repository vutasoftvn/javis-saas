import { describe, it, expect } from "vitest";
import { db } from "../models/db";
import { projects } from "../../shared/db/schema/operations";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { makeTenantContext } from "../../operations/tests/tenant-context.fixture";
import {
  createCampaignMvpService,
  listCampaignsMvpService,
  createExperimentMvpService,
  listExperimentsMvpService,
} from "../services/marketing-mvp.service";

async function makeProject(workspaceId: string): Promise<string> {
  const id = generateSnowflake();
  await db.insert(projects).values({ id, workspaceId: BigInt(workspaceId), title: "P" });
  return id.toString();
}

describe("Founder Trial marketing project scoping", () => {
  it("campaign create+list filter by project in SQL", async () => {
    const s = await createTestSession();
    const ctx = makeTenantContext({ workspaceId: s.workspaceId, userId: s.userId });
    const p1 = await makeProject(s.workspaceId);
    const p2 = await makeProject(s.workspaceId);

    await createCampaignMvpService(ctx, { name: "C for p1", projectId: p1 });
    await createCampaignMvpService(ctx, { name: "C for p2", projectId: p2 });
    // Founder Trial R1 — create không kèm projectId bị từ chối.
    await expect(
      createCampaignMvpService(ctx, { name: "C unscoped" })
    ).rejects.toThrow(/projectId is required/);

    const p1List = await listCampaignsMvpService(ctx, p1);
    expect(p1List.data.map((c) => c.name)).toEqual(["C for p1"]);
    expect(p1List.data[0].projectId).toBe(p1);

    // List cũng phải project-scoped.
    await expect(listCampaignsMvpService(ctx)).rejects.toThrow(/projectId is required/);
  });

  it("experiment create+list filter by project", async () => {
    const s = await createTestSession();
    const ctx = makeTenantContext({ workspaceId: s.workspaceId, userId: s.userId });
    const p1 = await makeProject(s.workspaceId);

    await createExperimentMvpService(ctx, {
      projectId: p1,
      name: "E1",
      hypothesis: "H",
    });
    await expect(
      createExperimentMvpService(ctx, { name: "E unscoped", hypothesis: "H" })
    ).rejects.toThrow(/projectId is required/);

    const scoped = await listExperimentsMvpService(ctx, p1);
    expect(scoped.data.map((e) => e.name)).toEqual(["E1"]);
    expect(scoped.data[0].projectId).toBe(p1);
  });

  it("rejects a campaign create with a cross-workspace projectId", async () => {
    const s = await createTestSession();
    const other = await createTestSession();
    const ctx = makeTenantContext({ workspaceId: s.workspaceId, userId: s.userId });
    const foreignProject = await makeProject(other.workspaceId);

    await expect(
      createCampaignMvpService(ctx, { name: "bad", projectId: foreignProject })
    ).rejects.toThrow();
  });
});
