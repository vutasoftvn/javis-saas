import { describe, it, expect } from "vitest";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { createProject } from "../../handlers/project.handler";
import { createTestWorkspaceWithMember } from "../../tests/_helpers";
import {
  getProjectActionContext,
  proposeNextActions,
  acceptActionProposal,
} from "../services/project-action-context.service";
import { createCycleService } from "../../services/twelve-week-year.service";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

const {
  assumptions,
  legalObligationInstances,
  nextBestActions,
  decisionRecords,
  weeklyCommitments,
} = schema;

describe("Project Action Context & Live Proposals (S4)", () => {
  async function seedProjectFixture() {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Action Context Project",
    });

    const ctx = {
      workspaceId: ws.workspaceId,
      userId: "1",
      membershipRole: "founder",
      permissions: [],
      correlationId: "action-ctx-test",
    };

    return { ws, project, ctx };
  }

  it("returns INSUFFICIENT_DATA when project has no assumptions instead of fake mock id=1", async () => {
    const { ctx, project } = await seedProjectFixture();

    const context = await getProjectActionContext(ctx, project.id);
    expect(context.assumptions.availability).toBe("UNAVAILABLE");

    const proposalResult = await proposeNextActions(ctx, project.id);
    expect(proposalResult.status).toBe("INSUFFICIENT_DATA");
    expect(proposalResult.items.length).toBe(0);
  });

  it("derives dynamic actions from real assumptions and preserves 64-bit snowflake IDs as strings", async () => {
    const { ctx, project, ws } = await seedProjectFixture();
    const wsId = BigInt(ws.workspaceId);
    const pId = BigInt(project.id);

    // Snowflake ID thật luôn > Number.MAX_SAFE_INTEGER (9007199254740991) — dùng
    // generateSnowflake() thay vì literal cố định để test lặp lại được trên DB
    // dev persistent (literal cũ để lại row vĩnh viễn, va PK ở lần chạy sau).
    const largeId = generateSnowflake();
    const largeIdStr = largeId.toString();

    await db.insert(assumptions).values({
      id: largeId,
      workspaceId: wsId,
      projectId: pId,
      statement: "Khách hàng sẵn sàng trả 500k/tháng",
      importance: 5,
      uncertainty: 4,
      riskScore: 20,
      status: "untested",
    });

    const context = await getProjectActionContext(ctx, project.id);
    expect(context.assumptions.availability).toBe("READY");
    if (context.assumptions.availability === "READY") {
      expect(context.assumptions.data.length).toBe(1);
      expect(context.assumptions.data[0]!.id).toBe(largeIdStr); // exact string match!
      expect(context.assumptions.data[0]!.statement).toBe("Khách hàng sẵn sàng trả 500k/tháng");
    }

    const proposals = await proposeNextActions(ctx, project.id);
    expect(proposals.status).toBe("READY");
    expect(proposals.items.length).toBe(1);
    expect(proposals.items[0]!.recommendation).toContain("Khách hàng sẵn sàng trả 500k/tháng");
    expect(proposals.items[0]!.source).toBe("evidence");
  });

  it("reflects OPEN legal obligations in context and proposes compliance actions", async () => {
    const { ctx, project, ws } = await seedProjectFixture();
    const wsId = BigInt(ws.workspaceId);

    // Also add an assumption so proposeNextActions proceeds
    await db.insert(assumptions).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: BigInt(project.id),
      statement: "Assumption for legal test",
      importance: 3,
      uncertainty: 3,
      riskScore: 9,
      status: "untested",
    });

    await db.insert(legalObligationInstances).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      title: "Đăng ký bảo vệ dữ liệu cá nhân Nghị định 13",
      source: "USER_CREATED",
      dueDate: "2026-10-01",
      status: "OPEN",
    });

    const context = await getProjectActionContext(ctx, project.id);
    expect(context.openObligations.availability).toBe("READY");
    if (context.openObligations.availability === "READY") {
      expect(context.openObligations.data.some((o) => o.title.includes("Nghị định 13"))).toBe(true);
    }

    const proposals = await proposeNextActions(ctx, project.id);
    expect(proposals.status).toBe("READY");
    const legalAction = proposals.items.find((i) => i.source === "legal");
    expect(legalAction).toBeDefined();
    expect(legalAction!.recommendation).toContain("Nghị định 13");
  });

  it("marks cashSummary and budgetSummary as UNAVAILABLE with reason instead of zero-filling", async () => {
    const { ctx, project } = await seedProjectFixture();

    const context = await getProjectActionContext(ctx, project.id);
    expect(context.cashSummary.availability).toBe("UNAVAILABLE");
    if (context.cashSummary.availability === "UNAVAILABLE") {
      expect(context.cashSummary.reason).toContain("F6");
    }

    expect(context.budgetSummary.availability).toBe("UNAVAILABLE");
    if (context.budgetSummary.availability === "UNAVAILABLE") {
      expect(context.budgetSummary.reason).toContain("F6");
    }
  });

  it("accepts action proposal, binds decision provenance, and idempotently handles replay", async () => {
    const { ctx, project, ws } = await seedProjectFixture();
    const wsId = BigInt(ws.workspaceId);

    // Create a cycle
    const cycle = await createCycleService({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      projectId: project.id,
      durationWeeks: 6,
      startLocalDate: "2026-09-07",
    });

    // Create a proposal
    const proposalId = generateSnowflake();
    await db.insert(nextBestActions).values({
      id: proposalId,
      workspaceId: wsId,
      projectId: BigInt(project.id),
      source: "evidence",
      recommendation: "Kiểm chứng nhu cầu qua 5 cuộc phỏng vấn sâu",
      priority: 1,
      status: "PROPOSED",
      decisionReason: "Cần xác thực problem trước khi build",
      revision: 1,
    });

    // Accept proposal
    const acceptRes = await acceptActionProposal(ctx, {
      proposalId: proposalId.toString(),
      expectedVersion: 1,
      cycleId: cycle.id,
      weekNo: 1,
    });

    expect(acceptRes.status).toBe("ACCEPTED");
    expect(acceptRes.decisionId).toBeTruthy();
    expect(acceptRes.commitmentId).toBeTruthy();
    expect(acceptRes.revision).toBe(2);

    // Verify decision record created in strategy.decision_records
    const [decision] = await db
      .select()
      .from(decisionRecords)
      .where(eq(decisionRecords.id, BigInt(acceptRes.decisionId)));
    expect(decision).toBeDefined();
    expect(decision!.decision).toBe("proceed");

    // Verify weekly commitment created with decisionId
    const [commitment] = await db
      .select()
      .from(weeklyCommitments)
      .where(eq(weeklyCommitments.id, BigInt(acceptRes.commitmentId!)));
    expect(commitment).toBeDefined();
    expect(commitment!.decisionId!.toString()).toBe(acceptRes.decisionId);
    expect(commitment!.title).toBe("Kiểm chứng nhu cầu qua 5 cuộc phỏng vấn sâu");

    // Replay accept: must be idempotent, not creating duplicate commitments
    const replayRes = await acceptActionProposal(ctx, {
      proposalId: proposalId.toString(),
      cycleId: cycle.id,
      weekNo: 1,
    });

    expect(replayRes.status).toBe("ACCEPTED");
    expect(replayRes.commitmentId).toBe(acceptRes.commitmentId);

    const commitmentCount = await db
      .select()
      .from(weeklyCommitments)
      .where(eq(weeklyCommitments.sourceActionId, proposalId.toString()));
    expect(commitmentCount.length).toBe(1); // exactly 1, no duplicate!
  });

  it("enforces tenant boundary: cannot accept proposal from another workspace", async () => {
    const { ctx, project } = await seedProjectFixture();
    const otherWs = await createTestWorkspaceWithMember();

    const proposalId = generateSnowflake();
    await db.insert(nextBestActions).values({
      id: proposalId,
      workspaceId: BigInt(otherWs.workspaceId), // different workspace!
      projectId: BigInt(project.id),
      source: "evidence",
      recommendation: "Other workspace action",
      priority: 1,
      status: "PROPOSED",
      decisionReason: "Boundary test",
    });

    await expect(
      acceptActionProposal(ctx, {
        proposalId: proposalId.toString(),
      })
    ).rejects.toThrow();
  });

  it("rejects a cycle that belongs to a different project (IA20)", async () => {
    const { ctx, project, ws } = await seedProjectFixture();
    const otherProject = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Other project, same workspace",
    });

    const otherCycle = await createCycleService({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      projectId: otherProject.id,
      durationWeeks: 6,
      startLocalDate: "2026-09-07",
    });

    const proposalId = generateSnowflake();
    await db.insert(nextBestActions).values({
      id: proposalId,
      workspaceId: BigInt(ws.workspaceId),
      projectId: BigInt(project.id),
      source: "evidence",
      recommendation: "Cross-project cycle attempt",
      priority: 1,
      status: "PROPOSED",
      decisionReason: "IA20 regression",
      revision: 1,
    });

    await expect(
      acceptActionProposal(ctx, {
        proposalId: proposalId.toString(),
        cycleId: otherCycle.id,
        weekNo: 1,
      })
    ).rejects.toThrow();

    const [reloaded] = await db
      .select()
      .from(nextBestActions)
      .where(eq(nextBestActions.id, proposalId));
    expect(reloaded!.status).toBe("PROPOSED"); // không được accept một phần
  });

  it("rejects a weekNo outside the cycle's actual duration (IA20)", async () => {
    const { ctx, project, ws } = await seedProjectFixture();

    const cycle = await createCycleService({
      workspaceId: ws.workspaceId,
      authorization: ws.bearerToken,
      projectId: project.id,
      durationWeeks: 6,
      startLocalDate: "2026-09-07",
    });

    const proposalId = generateSnowflake();
    await db.insert(nextBestActions).values({
      id: proposalId,
      workspaceId: BigInt(ws.workspaceId),
      projectId: BigInt(project.id),
      source: "evidence",
      recommendation: "Out-of-range weekNo attempt",
      priority: 1,
      status: "PROPOSED",
      decisionReason: "IA20 regression",
      revision: 1,
    });

    await expect(
      acceptActionProposal(ctx, {
        proposalId: proposalId.toString(),
        cycleId: cycle.id,
        weekNo: 999,
      })
    ).rejects.toThrow();
  });

  it("allows only one of two concurrent accepts on the same proposal to succeed (IA20)", async () => {
    const { ctx, project, ws } = await seedProjectFixture();

    const proposalId = generateSnowflake();
    await db.insert(nextBestActions).values({
      id: proposalId,
      workspaceId: BigInt(ws.workspaceId),
      projectId: BigInt(project.id),
      source: "evidence",
      recommendation: "Concurrent accept attempt",
      priority: 1,
      status: "PROPOSED",
      decisionReason: "IA20 regression",
      revision: 1,
    });

    const results = await Promise.allSettled([
      acceptActionProposal(ctx, { proposalId: proposalId.toString() }),
      acceptActionProposal(ctx, { proposalId: proposalId.toString() }),
    ]);

    const fulfilled = results.filter((r) => r.status === "fulfilled");
    expect(fulfilled.length).toBeGreaterThanOrEqual(1);

    const decisions = await db
      .select()
      .from(decisionRecords)
      .where(and(eq(decisionRecords.projectId, BigInt(project.id)), eq(decisionRecords.workspaceId, BigInt(ws.workspaceId))));
    expect(decisions.length).toBe(1); // không tạo 2 decision record trùng lặp
  });
});
