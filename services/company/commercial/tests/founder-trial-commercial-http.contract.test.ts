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
} from "../services/marketing-mvp.service";
import {
  createInterviewInWorkspace,
  submitInterviewAsEvidence,
} from "../../operations/strategy/services/interview.service";

async function makeProject(workspaceId: string): Promise<string> {
  const id = generateSnowflake();
  await db.insert(projects).values({ id, workspaceId: BigInt(workspaceId), title: "P" });
  return id.toString();
}

describe("Founder Trial commercial surface — project scope + tenant guards", () => {
  it("rejects a marketing pilot create/list without a projectId", async () => {
    const s = await createTestSession();
    const ctx = makeTenantContext({ workspaceId: s.workspaceId, userId: s.userId });

    await expect(
      createCampaignMvpService(ctx, { name: "no project" })
    ).rejects.toThrow(/projectId is required/i);
    await expect(listCampaignsMvpService(ctx)).rejects.toThrow(/projectId is required/i);
    await expect(
      createExperimentMvpService(ctx, { name: "no project", hypothesis: "h" })
    ).rejects.toThrow(/projectId is required/i);
  });

  it("rejects a campaign create pointed at another workspace's project", async () => {
    const a = await createTestSession();
    const b = await createTestSession();
    const ctxA = makeTenantContext({ workspaceId: a.workspaceId, userId: a.userId });
    const projectB = await makeProject(b.workspaceId);

    await expect(
      createCampaignMvpService(ctxA, { name: "wrong", projectId: projectB })
    ).rejects.toThrow(/project/i);
  });

  it("rejects submitting another workspace's interview as evidence", async () => {
    const a = await createTestSession();
    const b = await createTestSession();
    const ctxA = makeTenantContext({ workspaceId: a.workspaceId, userId: a.userId });
    const ctxB = makeTenantContext({ workspaceId: b.workspaceId, userId: b.userId });

    const projectA = await makeProject(a.workspaceId);
    const interviewA = await createInterviewInWorkspace(ctxA, {
      projectId: projectA,
      notes: "Founder talked to five ops leads",
    });

    await expect(
      submitInterviewAsEvidence(ctxB, interviewA.id, { claim: "steal" })
    ).rejects.toThrow();
  });
});
