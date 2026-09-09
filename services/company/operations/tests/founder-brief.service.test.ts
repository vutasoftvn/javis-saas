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
  return {
    ws,
    project,
    ctx: makeTenantContext(ws),
    founderCtx: makeTenantContext(ws, { membershipRole: "founder" }),
  };
}

describe("Founder Brief (coverage-only, deterministic, no verdict)", () => {
  it("reports NO_EVIDENCE / CONFIGURATION_REQUIRED axes and a non-authoritative review focus", async () => {
    const { project, ctx } = await seed();
    await createAssumptionInWorkspace(ctx, {
      projectId: project.id,
      statement: "Weekly pain",
      importance: 9,
      uncertainty: 8,
    });

    const brief = await getFounderBrief(ctx, project.id);
    expect(brief.axes.map((a) => a.axis)).toEqual([
      "problem",
      "solution",
      "traction",
      "economics",
      "compliance",
    ]);

    const problem = brief.axes.find((a) => a.axis === "problem")!;
    expect(problem.state).toBe("NO_EVIDENCE");
    expect(problem.knownGaps.join(" ")).toContain("chưa kiểm chứng");

    expect(brief.axes.find((a) => a.axis === "compliance")!.state).toBe("NOT_ASSESSED");

    const economics = brief.axes.find((a) => a.axis === "economics")! as any;
    expect(economics.projectBudget.state).toBe("CONFIGURATION_REQUIRED");
    expect(economics.workspaceLiquidity.state).toBe("CONFIGURATION_REQUIRED");

    expect(brief.nextReviewFocus.isAuthoritative).toBe(false);
    expect(brief.nextReviewFocus.axis).toBe("problem");
    expect(brief.generatedFrom).toBe("deterministic_rules");
    // Không còn field mang tính quyết định.
    expect((brief as any).suggestedDecision).toBeUndefined();
  });

  it("moves problem + solution to EVIDENCE_PRESENT once linked evidence is approved", async () => {
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
    expect(brief.axes.find((a) => a.axis === "problem")!.state).toBe("EVIDENCE_PRESENT");
    expect(brief.axes.find((a) => a.axis === "problem")!.evidenceRefs).toContain(ev.id);
    expect(brief.axes.find((a) => a.axis === "solution")!.state).toBe("EVIDENCE_PRESENT");
    // Còn economics chưa cấu hình -> review focus trỏ economics.
    expect(brief.nextReviewFocus.axis).toBe("economics");
  });

  it("refuses a project from another workspace", async () => {
    const { project } = await seed();
    const other = await createTestWorkspaceWithMember();
    const ctxOther = makeTenantContext(other);
    await expect(getFounderBrief(ctxOther, project.id)).rejects.toThrow();
  });
});
