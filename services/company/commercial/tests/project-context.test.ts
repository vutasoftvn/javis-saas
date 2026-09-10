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
import { createContactService } from "../services/contact.service";
import { createSalesLeadService } from "../services/lead.service";
import {
  createInterviewInWorkspace,
  submitInterviewAsEvidence,
} from "../../operations/strategy/services/interview.service";

async function makeProject(workspaceId: string, title = "Test Project"): Promise<string> {
  const id = generateSnowflake();
  await db.insert(projects).values({ id, workspaceId: BigInt(workspaceId), title });
  return id.toString();
}

describe("Commercial & Marketing Project Context Scoping", () => {
  it("rejects creating marketing campaign with another workspace's projectId", async () => {
    const a = await createTestSession();
    const b = await createTestSession();
    const ctxA = makeTenantContext({ workspaceId: a.workspaceId, userId: a.userId });
    const projectB = await makeProject(b.workspaceId);

    await expect(
      createCampaignMvpService(ctxA, { name: "Cross Project Campaign", projectId: projectB })
    ).rejects.toThrow(/project/i);
  });

  it("rejects creating marketing experiment with another workspace's projectId", async () => {
    const a = await createTestSession();
    const b = await createTestSession();
    const ctxA = makeTenantContext({ workspaceId: a.workspaceId, userId: a.userId });
    const projectB = await makeProject(b.workspaceId);

    await expect(
      createExperimentMvpService(ctxA, {
        name: "Cross Project Experiment",
        hypothesis: "Hypothesis",
        projectId: projectB,
      })
    ).rejects.toThrow(/project/i);
  });

  it("rejects linking contact to another workspace's projectId", async () => {
    const a = await createTestSession();
    const b = await createTestSession();
    const projectB = await makeProject(b.workspaceId);

    await expect(
      createContactService(
        {
          workspaceId: a.workspaceId,
          name: "Cross Project Contact",
          projectId: projectB,
        },
        "Bearer " + a.accessToken
      )
    ).rejects.toThrow(/project/i);
  });

  it("rejects linking sales lead to another workspace's projectId", async () => {
    const a = await createTestSession();
    const b = await createTestSession();
    const projectB = await makeProject(b.workspaceId);

    await expect(
      createSalesLeadService(
        {
          workspaceId: a.workspaceId,
          name: "Cross Project Lead",
          projectId: projectB,
        },
        "Bearer " + a.accessToken
      )
    ).rejects.toThrow(/project/i);
  });

  it("rejects submitting interview evidence across workspaces", async () => {
    const a = await createTestSession();
    const b = await createTestSession();
    const ctxA = makeTenantContext({ workspaceId: a.workspaceId, userId: a.userId });
    const ctxB = makeTenantContext({ workspaceId: b.workspaceId, userId: b.userId });

    const projectA = await makeProject(a.workspaceId);
    const interviewA = await createInterviewInWorkspace(ctxA, {
      projectId: projectA,
      notes: "Customer Interview 1",
    });

    await expect(
      submitInterviewAsEvidence(ctxB, interviewA.id, { claim: "Unauthorized claim" })
    ).rejects.toThrow();
  });
});
