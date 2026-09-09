import { describe, it, expect } from "vitest";
import { makeTenantContext } from "./tenant-context.fixture";
import { createTestWorkspaceWithMember } from "./_helpers";
import { createProject } from "../handlers/project.handler";
import { createAssumptionInWorkspace } from "../strategy/services/assumption.service";
import { createFounderTrialExperiment } from "../strategy/services/experiment-proposal.service";
import { recordEvidenceInWorkspace } from "../strategy/services/evidence-lifecycle.service";
import { reviewEvidenceInWorkspace } from "../strategy/services/evidence-review.service";
import { getFounderBrief } from "../strategy/services/founder-brief.service";

async function seed() {
  const ws = await createTestWorkspaceWithMember();
  const project = await createProject({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    title: "Founder Brief project",
  });
  return { ws, project, ctx: makeTenantContext(ws), founderCtx: makeTenantContext(ws, { membershipRole: "founder" }) };
}

describe("Founder Brief (deterministic, no agent recommendation)", () => {
  it("reports no_evidence axes and a continue-discovery suggestion for a fresh project", async () => {
    const { project, ctx } = await seed();
    await createAssumptionInWorkspace(ctx, {
      projectId: project.id,
      statement: "Weekly pain",
      importance: 9,
      uncertainty: 8,
    });

    const brief = await getFounderBrief(ctx, project.id);
    const axisKeys = brief.axes.map((a) => a.axis);
    expect(axisKeys).toEqual(["problem", "solution", "traction", "economics", "compliance"]);

    const problem = brief.axes.find((a) => a.axis === "problem")!;
    expect(problem.state).toBe("no_evidence");
    expect(problem.knownGaps.join(" ")).toContain("chưa kiểm chứng");

    expect(brief.axes.find((a) => a.axis === "compliance")!.state).toBe("not_assessed");
    expect(brief.axes.find((a) => a.axis === "economics")!.state).toBe("configuration_required");

    expect(brief.suggestedDecision.isAuthoritative).toBe(false);
    expect(brief.suggestedDecision.label).toBe("proceed");
    expect(brief.generatedFrom).toBe("deterministic_rules");
  });

  it("moves the problem axis to emerging once linked evidence is approved", async () => {
    const { project, ctx, founderCtx } = await seed();
    const a = await createAssumptionInWorkspace(ctx, {
      projectId: project.id,
      statement: "Weekly pain",
      importance: 9,
      uncertainty: 8,
    });
    const exp = await createFounderTrialExperiment(ctx, {
      projectId: project.id,
      assumptionId: a.id,
      hypothesis: "5/10 confirm",
      method: "customer_interview",
      successCriteria: "5 of 10",
    });
    const ev = await recordEvidenceInWorkspace(ctx, {
      projectId: project.id,
      experimentId: exp.id,
      sourceType: "interview",
      claim: "6/10 confirmed",
      status: "candidate",
    });
    await reviewEvidenceInWorkspace(founderCtx, { id: ev.id, action: "approve" });

    const brief = await getFounderBrief(ctx, project.id);
    const problem = brief.axes.find((a) => a.axis === "problem")!;
    expect(problem.state).toBe("emerging");
    expect(problem.evidenceRefs).toContain(ev.id);
    // Problem has some support but solution not validated (1 approved ev) → still emerging/hold path.
    expect(["hold", "proceed"]).toContain(brief.suggestedDecision.label);
  });

  it("refuses a project from another workspace", async () => {
    const { project } = await seed();
    const other = await createTestWorkspaceWithMember();
    const ctxOther = makeTenantContext(other);
    await expect(getFounderBrief(ctxOther, project.id)).rejects.toThrow();
  });
});
