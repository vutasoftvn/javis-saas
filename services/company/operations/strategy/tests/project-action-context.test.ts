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

  it("IA28: keeps an IN_PROGRESS obligation visible in active context, not just OPEN", async () => {
    const { ctx, project, ws } = await seedProjectFixture();
    const wsId = BigInt(ws.workspaceId);

    await db.insert(legalObligationInstances).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      title: "Nghĩa vụ đang xử lý (IN_PROGRESS)",
      source: "USER_CREATED",
      dueDate: "2026-10-01",
      status: "IN_PROGRESS",
    });

    const context = await getProjectActionContext(ctx, project.id);
    expect(context.openObligations.availability).toBe("READY");
    if (context.openObligations.availability === "READY") {
      // Trước IA28: query chỉ lọc status="OPEN" nên nghĩa vụ IN_PROGRESS
      // biến mất khỏi active context dù chưa đóng (chưa FULFILLED/EXEMPT/
      // CANCELLED) — agent/người xem context sẽ tưởng nhầm là không còn
      // nghĩa vụ pháp lý nào đang chờ xử lý.
      expect(context.openObligations.data.some((o) => o.title.includes("IN_PROGRESS"))).toBe(true);
    }
  });

  it("marks cashSummary UNAVAILABLE with a real reason when no finance snapshot exists yet", async () => {
    const { ctx, project } = await seedProjectFixture();

    const context = await getProjectActionContext(ctx, project.id);
    expect(context.cashSummary.availability).toBe("UNAVAILABLE");
    if (context.cashSummary.availability === "UNAVAILABLE") {
      expect(context.cashSummary.reason).not.toContain("F6");
    }
  });

  it("keeps runwayMonths NULL (cash-flow dương) instead of zero-filling it to 0 (hết tiền)", async () => {
    const { ctx, project } = await seedProjectFixture();

    // Không có bank transaction nào => monthlyNetBurn = 0 => cashFlowPositive
    // => financial-snapshot.service ghi runway_months = NULL có chủ đích
    // ("null khi cashFlowPositive; BỎ hard-code 99").
    const { calculateAndSaveSnapshotService } = await import(
      "../../../finance-legal/services/financial-snapshot.service"
    );
    const snapshot = await calculateAndSaveSnapshotService({
      workspaceId: BigInt(ctx.workspaceId),
      snapshotDate: "2026-09-01",
      openingBalance: "50000000",
    });
    expect(snapshot.cashFlowPositive).toBe(true);
    expect(snapshot.runwayMonths).toBeNull();

    const context = await getProjectActionContext(ctx, project.id);
    expect(context.cashSummary.availability).toBe("READY");
    if (context.cashSummary.availability === "READY") {
      // Đây là điểm mấu chốt: map null -> 0 sẽ nói NGƯỢC sự thật với người
      // hoặc agent đọc context ("còn 0 tháng tiền" thay vì "dòng tiền dương,
      // không có trần runway").
      expect(context.cashSummary.data.runwayMonths).toBeNull();
      expect(context.cashSummary.data.cashBalance).toBe(50000000);
      expect(context.cashSummary.data.monthlyBurn).toBe(0);
    }
  });

  it("passes through a real runwayMonths number when the workspace is burning cash", async () => {
    const { ctx, project } = await seedProjectFixture();
    const wsId = BigInt(ctx.workspaceId);

    const { createBankConnectionService } = await import(
      "../../../finance-legal/services/bank-connection.service"
    );
    const conn = await createBankConnectionService({ workspaceId: wsId, provider: "manual" });
    await db.insert(schema.bankTransactions).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      bankConnectionId: BigInt(conn.id),
      externalTransactionId: `ext-burn-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      postedAt: new Date("2026-09-10T00:00:00Z"),
      amount: "3000000.00",
      currency: "VND",
      direction: "OUT",
      description: "Chi phi van hanh thang 9",
      status: "UNRECONCILED",
    });

    const { calculateAndSaveSnapshotService } = await import(
      "../../../finance-legal/services/financial-snapshot.service"
    );
    // Cửa sổ burn mặc định 3 tháng: 3.000.000 / 3 = 1.000.000/tháng;
    // currentCash = 50.000.000 - 3.000.000 = 47.000.000 => runway 47 tháng.
    const snapshot = await calculateAndSaveSnapshotService({
      workspaceId: wsId,
      snapshotDate: "2026-09-30",
      openingBalance: "50000000",
    });
    expect(snapshot.cashFlowPositive).toBe(false);
    expect(Number(snapshot.runwayMonths)).toBe(47);

    const context = await getProjectActionContext(ctx, project.id);
    expect(context.cashSummary.availability).toBe("READY");
    if (context.cashSummary.availability === "READY") {
      expect(context.cashSummary.data.runwayMonths).toBe(47);
      expect(context.cashSummary.data.cashBalance).toBe(47000000);
      expect(context.cashSummary.data.monthlyBurn).toBe(1000000);
    }
  });

  it("marks budgetSummary UNAVAILABLE when the project has no budget envelope, READY with real numbers once one exists", async () => {
    const { ctx, project } = await seedProjectFixture();

    const before = await getProjectActionContext(ctx, project.id);
    expect(before.budgetSummary.availability).toBe("UNAVAILABLE");
    if (before.budgetSummary.availability === "UNAVAILABLE") {
      expect(before.budgetSummary.reason).not.toContain("F6");
    }

    const { createBudgetEnvelopeService } = await import(
      "../../../finance-legal/services/budget-summary.service"
    );
    const { createLegalEntityProfile } = await import(
      "../../../finance-legal/services/legal-entity-profile.service"
    );
    const entity = await createLegalEntityProfile({
      workspaceId: BigInt(ctx.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });
    await createBudgetEnvelopeService(ctx, {
      projectId: project.id,
      legalEntityId: entity.id,
      periodStart: "2020-01-01",
      periodEnd: "2030-12-31",
      limitMinor: "5000000",
    });

    const after = await getProjectActionContext(ctx, project.id);
    expect(after.budgetSummary.availability).toBe("READY");
    if (after.budgetSummary.availability === "READY") {
      expect(after.budgetSummary.data.totalBudget).toBe(5000000);
      expect(after.budgetSummary.data.remaining).toBe(5000000);
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
