import { describe, it, expect } from "vitest";
import { makeTenantContext } from "./tenant-context.fixture";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import { createProject } from "../handlers/project.handler";
import { getFounderTrialBoard } from "../strategy/services/founder-trial-board.service";
import { createAssumptionInWorkspace } from "../strategy/services/assumption.service";
import { createExperimentInWorkspace } from "../strategy/services/experiment-proposal.service";
import { recordEvidenceInWorkspace } from "../strategy/services/evidence-lifecycle.service";
import { reviewEvidenceInWorkspace } from "../strategy/services/evidence-review.service";
import { createDecisionRecordInWorkspace } from "../strategy/services/decision-recording.service";

async function seedProject() {
  const ws = await createTestWorkspaceWithMember();
  const project = await createProject({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    title: "Founder Trial Board project",
  });
  const ctx = makeTenantContext(ws);
  const founderCtx = makeTenantContext(ws, { membershipRole: "founder" });
  return { ws, project, ctx, founderCtx };
}

describe("Founder Trial Board read model", () => {
  it("composes assumptions, experiments, evidence and decisions for one project", async () => {
    const { project, ctx, founderCtx } = await seedProject();

    const a1 = await createAssumptionInWorkspace(ctx, {
      projectId: project.id,
      statement: "Customers feel this pain weekly",
      importance: 9,
      uncertainty: 8,
    });
    await createAssumptionInWorkspace(ctx, {
      projectId: project.id,
      statement: "They will pay 20 USD/month",
      importance: 5,
      uncertainty: 5,
    });

    const exp = await createExperimentInWorkspace(ctx, {
      projectId: project.id,
      assumptionId: a1.id,
      hypothesis: "5/10 interviews confirm weekly pain",
      method: "customer_interview",
      successCriteria: "At least 5 of 10 confirm",
    });

    const linked = await recordEvidenceInWorkspace(ctx, {
      projectId: project.id,
      experimentId: exp.id,
      sourceType: "interview",
      claim: "6/10 confirmed the weekly pain",
      status: "candidate",
    });
    await reviewEvidenceInWorkspace(founderCtx, { id: linked.id, action: "approve" });

    await recordEvidenceInWorkspace(ctx, {
      projectId: project.id,
      sourceType: "interview",
      claim: "Loose note, not tied to a hypothesis",
      status: "candidate",
    });

    await createDecisionRecordInWorkspace(founderCtx, {
      projectId: project.id,
      decision: "proceed",
    });

    const board = await getFounderTrialBoard(ctx, project.id);

    expect(board.projectId).toBe(project.id);
    expect(board.assumptions).toHaveLength(2);
    expect(board.assumptions[0].statement).toContain("weekly"); // higher risk score ranks first
    expect(board.assumptions.filter((a) => a.isFocus).length).toBeGreaterThanOrEqual(1);

    expect(board.experiments).toHaveLength(1);
    expect(board.experiments[0].linkedToAssumption).toBe(true);

    expect(board.evidence.approved).toHaveLength(1);
    expect(board.evidence.approved[0].linkedToExperiment).toBe(true);
    expect(board.evidence.candidate.map((e) => e.claim)).toContain(
      "Loose note, not tied to a hypothesis"
    );
    expect(board.evidence.unlinked).toHaveLength(1);
    expect(board.evidence.unlinked[0].linkedToExperiment).toBe(false);

    expect(board.decisions).toHaveLength(1);
    expect(board.decisions[0].decision).toBe("proceed");
  });

  it("marks only the top 3 untested assumptions as focus", async () => {
    const { project, ctx } = await seedProject();
    for (let i = 0; i < 5; i++) {
      await createAssumptionInWorkspace(ctx, {
        projectId: project.id,
        statement: `Assumption ${i}`,
        importance: 9 - i,
        uncertainty: 9,
      });
    }
    const board = await getFounderTrialBoard(ctx, project.id);
    expect(board.assumptions).toHaveLength(5);
    expect(board.assumptions.filter((a) => a.isFocus)).toHaveLength(3);
    // Focus = 3 assumption risk cao nhất
    expect(board.assumptions.slice(0, 3).every((a) => a.isFocus)).toBe(true);
  });

  it("refuses a project from another workspace", async () => {
    const { project } = await seedProject();
    const wsB = await createSecondWorkspace();
    const ctxB = makeTenantContext({ workspaceId: wsB.workspaceId, userId: "1" });
    await expect(getFounderTrialBoard(ctxB, project.id)).rejects.toThrow();
  });

  it("returns an empty-but-typed board for a project with no strategy data yet", async () => {
    const { project, ctx } = await seedProject();
    const board = await getFounderTrialBoard(ctx, project.id);
    expect(board.assumptions).toEqual([]);
    expect(board.experiments).toEqual([]);
    expect(board.evidence.candidate).toEqual([]);
    expect(board.evidence.approved).toEqual([]);
    expect(board.decisions).toEqual([]);
    expect(board.cycle).toHaveProperty("reviews");
  });
});
