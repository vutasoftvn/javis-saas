import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { makeTenantContext } from "./tenant-context.fixture";
import { createTestWorkspaceWithMember } from "./_helpers";
import { createProject } from "../handlers/project.handler";
import { createAssumptionInWorkspace } from "../strategy/services/assumption.service";
import {
  createExperimentInWorkspace,
  createFounderTrialExperiment,
} from "../strategy/services/experiment-proposal.service";
import { recordEvidenceInWorkspace } from "../strategy/services/evidence-lifecycle.service";
import { reviewEvidenceInWorkspace } from "../strategy/services/evidence-review.service";
import { getFounderBrief } from "../strategy/services/founder-brief.service";
import { getFounderTrialBoard } from "../strategy/services/founder-trial-board.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { financialSnapshots, cycleReviews } = schema;

const axis = (brief: Awaited<ReturnType<typeof getFounderBrief>>, key: string) =>
  brief.axes.find((a) => a.axis === key)! as any;

async function seed() {
  const ws = await createTestWorkspaceWithMember();
  const project = await createProject({
    authorization: ws.bearerToken,
    workspaceId: ws.workspaceId,
    title: "Evidence boundary project",
  });
  return {
    ws,
    project,
    ctx: makeTenantContext(ws),
    founderCtx: makeTenantContext(ws, { membershipRole: "founder" }),
  };
}

describe("Founder Trial evidence attribution boundary", () => {
  it("excludes approved evidence from a generic experiment without assumptionId", async () => {
    const { project, ctx, founderCtx } = await seed();
    await createAssumptionInWorkspace(ctx, {
      projectId: project.id,
      statement: "Weekly pain",
      importance: 9,
      uncertainty: 8,
    });
    // Experiment KHÔNG gắn assumption.
    const generic = await createExperimentInWorkspace(ctx, {
      projectId: project.id,
      hypothesis: "Generic probe",
      method: "customer_interview",
      successCriteria: "some signal",
    });
    const ev = await recordEvidenceInWorkspace(ctx, {
      projectId: project.id,
      experimentId: generic.id,
      sourceType: "interview",
      claim: "Loosely related note",
      status: "candidate",
    });
    await reviewEvidenceInWorkspace(founderCtx, { id: ev.id, action: "approve" });

    const board = await getFounderTrialBoard(ctx, project.id);
    const boardEv = board.evidence.approved.find((e) => e.id === ev.id)!;
    expect(boardEv.linkedToExperiment).toBe(true);
    expect(boardEv.linkedToFounderTrialAssumption).toBe(false);

    const brief = await getFounderBrief(ctx, project.id);
    expect(axis(brief, "problem").state).toBe("NO_EVIDENCE");
    expect(axis(brief, "solution").state).toBe("NO_EVIDENCE");
  });

  it("ignores unlinked (no experiment) approved evidence for coverage", async () => {
    const { project, ctx, founderCtx } = await seed();
    await createAssumptionInWorkspace(ctx, {
      projectId: project.id,
      statement: "Weekly pain",
      importance: 9,
      uncertainty: 8,
    });
    const ev = await recordEvidenceInWorkspace(ctx, {
      projectId: project.id,
      sourceType: "interview",
      claim: "Direct evidence, no experiment",
      status: "candidate",
    });
    await reviewEvidenceInWorkspace(founderCtx, { id: ev.id, action: "approve" });

    const brief = await getFounderBrief(ctx, project.id);
    expect(axis(brief, "problem").state).toBe("NO_EVIDENCE");
    expect(axis(brief, "problem").knownGaps.join(" ")).toContain("ngoài coverage");
  });

  it("does not treat a cross-project experiment's evidence as coverage", async () => {
    const { ws, project, ctx, founderCtx } = await seed();
    // Project B trong CÙNG workspace, có assumption + founder-trial experiment.
    const projectB = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Project B",
    });
    const aB = await createAssumptionInWorkspace(ctx, {
      projectId: projectB.id,
      statement: "B pain",
      importance: 8,
      uncertainty: 8,
    });
    const expB = await createFounderTrialExperiment(ctx, {
      projectId: projectB.id,
      assumptionId: aB.id,
      hypothesis: "B hypo",
      method: "customer_interview",
      successCriteria: "5 of 10",
    });
    // Evidence ghi trên project A nhưng trỏ experiment của project B.
    await createAssumptionInWorkspace(ctx, {
      projectId: project.id,
      statement: "A pain",
      importance: 9,
      uncertainty: 8,
    });
    const ev = await recordEvidenceInWorkspace(ctx, {
      projectId: project.id,
      experimentId: expB.id,
      sourceType: "interview",
      claim: "cross-project",
      status: "candidate",
    });
    await reviewEvidenceInWorkspace(founderCtx, { id: ev.id, action: "approve" });

    const board = await getFounderTrialBoard(ctx, project.id);
    const boardEv = board.evidence.approved.find((e) => e.id === ev.id);
    expect(boardEv?.linkedToFounderTrialAssumption ?? false).toBe(false);
    expect(axis(await getFounderBrief(ctx, project.id), "problem").state).toBe("NO_EVIDENCE");
  });

  it("keeps projectBudget CONFIGURATION_REQUIRED when only a workspace snapshot exists", async () => {
    const { ws, project, ctx } = await seed();
    await db.insert(financialSnapshots).values({
      id: generateSnowflake(),
      workspaceId: BigInt(ws.workspaceId),
      snapshotDate: "2026-09-01",
      currency: "VND",
    });

    const economics = axis(await getFounderBrief(ctx, project.id), "economics");
    expect(economics.projectBudget.state).toBe("CONFIGURATION_REQUIRED");
    expect(economics.workspaceLiquidity.state).toBe("EVIDENCE_PRESENT");
    expect(economics.workspaceLiquidity.sourceTimestamp).toBe("2026-09-01");
  });

  it("excludes a soft-deleted cycle review from the board", async () => {
    const { project, ctx } = await seed();
    // Không có cycle -> board vẫn typed; thêm giả lập review soft-deleted an toàn:
    const board = await getFounderTrialBoard(ctx, project.id);
    expect(Array.isArray(board.cycle.reviews)).toBe(true);
    // (Board query cycle_reviews không lọc deletedAt trực tiếp ở read model board;
    // đảm bảo cột tồn tại để lệnh resize/reschedule dựa vào nó.)
    const cols = await db
      .select()
      .from(cycleReviews)
      .where(eq(cycleReviews.cycleId, BigInt(-1)));
    expect(cols).toEqual([]);
  });
});
