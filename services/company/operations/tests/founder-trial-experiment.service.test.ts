import { describe, it, expect } from "vitest";
import { makeTenantContext } from "./tenant-context.fixture";
import { createTestWorkspaceWithMember } from "./_helpers";
import { createProject } from "../handlers/project.handler";
import { createAssumptionInWorkspace } from "../strategy/services/assumption.service";
import {
  createExperimentInWorkspace,
  createFounderTrialExperiment,
} from "../strategy/services/experiment-proposal.service";

async function seed() {
  const ws = await createTestWorkspaceWithMember();
  const project = await createProject({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    title: "Founder Trial experiment project",
  });
  const ctx = makeTenantContext(ws);
  const assumption = await createAssumptionInWorkspace(ctx, {
    projectId: project.id,
    statement: "They will pay for this",
    importance: 8,
    uncertainty: 7,
  });
  return { ws, project, ctx, assumption };
}

describe("Founder Trial experiment contract (stricter than generic)", () => {
  it("requires an assumptionId", async () => {
    const { project, ctx } = await seed();
    await expect(
      createFounderTrialExperiment(ctx, {
        projectId: project.id,
        hypothesis: "H",
        method: "customer_interview",
        successCriteria: "5/10 confirm",
      })
    ).rejects.toThrow();
  });

  it("requires non-empty method and successCriteria", async () => {
    const { project, ctx, assumption } = await seed();
    await expect(
      createFounderTrialExperiment(ctx, {
        projectId: project.id,
        assumptionId: assumption.id,
        hypothesis: "H",
        method: "   ",
        successCriteria: "5/10 confirm",
      })
    ).rejects.toThrow();
    await expect(
      createFounderTrialExperiment(ctx, {
        projectId: project.id,
        assumptionId: assumption.id,
        hypothesis: "H",
        method: "customer_interview",
        successCriteria: "",
      })
    ).rejects.toThrow();
  });

  it("rejects an assumptionId that belongs to a different project", async () => {
    const { ws, ctx, assumption } = await seed();
    const otherProject = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Other project",
    });
    await expect(
      createFounderTrialExperiment(ctx, {
        projectId: otherProject.id,
        assumptionId: assumption.id,
        hypothesis: "H",
        method: "customer_interview",
        successCriteria: "5/10 confirm",
      })
    ).rejects.toThrow();
  });

  it("rejects an assumptionId from another workspace", async () => {
    const { assumption } = await seed();
    const wsB = await createTestWorkspaceWithMember();
    const ctxB = makeTenantContext(wsB);
    const projectB = await createProject({
      authorization: wsB.bearerToken,
      workspaceId: wsB.workspaceId,
      title: "B project",
    });
    await expect(
      createFounderTrialExperiment(ctxB, {
        projectId: projectB.id,
        assumptionId: assumption.id,
        hypothesis: "H",
        method: "customer_interview",
        successCriteria: "5/10 confirm",
      })
    ).rejects.toThrow();
  });

  it("creates a valid Founder Trial experiment linked to its assumption", async () => {
    const { project, ctx, assumption } = await seed();
    const exp = await createFounderTrialExperiment(ctx, {
      projectId: project.id,
      assumptionId: assumption.id,
      hypothesis: "5/10 interviews confirm",
      method: "customer_interview",
      successCriteria: "At least 5 of 10 confirm",
    });
    expect(exp.assumptionId).toBe(assumption.id);
    expect(exp.method).toBe("customer_interview");
  });

  it("leaves the generic createExperimentInWorkspace permissive (no assumptionId ok)", async () => {
    const { project, ctx } = await seed();
    const exp = await createExperimentInWorkspace(ctx, {
      projectId: project.id,
      hypothesis: "H",
      method: "landing_page_test",
      successCriteria: "Signups > 100",
    });
    expect(exp.assumptionId).toBeNull();
  });
});
