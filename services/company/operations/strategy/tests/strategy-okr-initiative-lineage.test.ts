import { describe, expect, it } from "vitest";
import { APIError } from "encore.dev/api";
import { createTestWorkspaceWithMember } from "../../tests/_helpers";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import { db } from "../../models/db";
import { okrObjectives, initiatives } from "../../../shared/db/schema/operations";
import { decisionRecords } from "../../../shared/db/schema/strategy";
import { eq } from "drizzle-orm";
import {
  createStrategicObjective,
} from "../services/strategic-objective.service";
import {
  createTowsOption,
  createTowsOptionEvaluation,
  selectTowsOption,
} from "../services/tows-option.service";
import {
  createOkrCycleService,
  createObjectiveService,
  addKeyResultService,
  publishObjectiveService,
  getObjectiveService,
} from "../../services/okr.service";
import {
  createInitiativeService,
  getInitiativeService,
  approveInitiativeService,
  listInitiativesService,
  updateInitiativeService,
} from "../../services/initiative.service";
import {
  updateWorkspaceStrategySettings,
} from "../services/workspace-strategy-settings.service";

function createMockTenantContext(
  overrides: Partial<TenantContext> & {
    workspaceId: string;
    userId: string;
    membershipRole: string;
  }
): TenantContext {
  return {
    permissions: [],
    correlationId: "test-corr-id",
    ...overrides,
  };
}

describe("strategy-okr-initiative-lineage service", () => {
  it("rejects OKR objective creation referencing an unselected TOWS option, and succeeds when selected", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    await updateWorkspaceStrategySettings(ctx, {
      workspaceId: ws.workspaceId,
      bscMode: "OFF",
    });

    const cycle = await createOkrCycleService({
      workspaceId: ws.workspaceId,
      name: "Chu kỳ Q1 2026",
      authorization: ws.bearerToken,
    });

    const stratObj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Mở rộng thị phần quốc tế",
      successDefinition: "Đạt 1M ARR ngoài nước",
      status: "ACTIVE",
    });

    const draftTows = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: stratObj.id,
      quadrant: "SO",
      title: "Thâm nhập thị trường Singapore",
    });

    // 1. Try to create OKR objective with unselected TOWS option -> Fails
    await expect(
      createObjectiveService({
        workspaceId: ws.workspaceId,
        cycleId: cycle.id,
        title: "Xây dựng đội ngũ Singapore",
        strategicObjectiveId: stratObj.id,
        towsOptionId: draftTows.id,
        authorization: ws.bearerToken,
      })
    ).rejects.toThrow("TOWS option must be SELECTED");

    // 2. Evaluate and select the TOWS option
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: draftTows.id,
      impactScore: 5,
      difficultyScore: 2,
    });
    await selectTowsOption({ id: draftTows.id }, ctx);

    // 3. Now create OKR objective -> Succeeds
    const okrObj = await createObjectiveService({
      workspaceId: ws.workspaceId,
      cycleId: cycle.id,
      title: "Xây dựng đội ngũ Singapore",
      strategicObjectiveId: stratObj.id,
      towsOptionId: draftTows.id,
      authorization: ws.bearerToken,
    });

    expect(okrObj.strategicObjectiveId).toBe(stratObj.id);
    expect(okrObj.towsOptionId).toBe(draftTows.id);
    expect(okrObj.status).toBe("draft");
  });

  it("enforces 1-3 Key Results publish policy with contract validation", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    const cycle = await createOkrCycleService({
      workspaceId: ws.workspaceId,
      name: "Chu kỳ Q1 2026",
      authorization: ws.bearerToken,
    });

    const okrObj = await createObjectiveService({
      workspaceId: ws.workspaceId,
      cycleId: cycle.id,
      title: "Tăng trưởng doanh thu sản phẩm A",
      authorization: ws.bearerToken,
    });

    // 0 Key Results -> Publish rejected
    await expect(
      publishObjectiveService({ id: okrObj.id }, ctx)
    ).rejects.toThrow("between 1 and 3 Key Results");

    // Add 1 valid KR
    await addKeyResultService({
      objectiveId: okrObj.id,
      title: "Doanh thu đạt 500k USD",
      targetValue: 500000,
      baselineValue: 100000,
      scoringType: "LINEAR_INCREASE",
      unit: "USD",
      authorization: ws.bearerToken,
    });

    // Add 2nd valid KR
    await addKeyResultService({
      objectiveId: okrObj.id,
      title: "Số khách hàng mới đạt 50",
      targetValue: 50,
      baselineValue: 10,
      scoringType: "LINEAR_INCREASE",
      unit: "khách hàng",
      authorization: ws.bearerToken,
    });

    // Publish with 2 KRs -> Succeeds
    const published = await publishObjectiveService({ id: okrObj.id }, ctx);
    expect(published.status).toBe("published");
    expect(published.publishedAt).toBeDefined();
    expect(published.publishedByMemberId).toBeDefined();

    // The fourth KR is rejected immediately, keeping the OKR measurable.
    const objWith4Krs = await createObjectiveService({
      workspaceId: ws.workspaceId,
      cycleId: cycle.id,
      title: "Mục tiêu 4 KRs",
      authorization: ws.bearerToken,
    });

    for (let i = 1; i <= 3; i++) {
      await addKeyResultService({
        objectiveId: objWith4Krs.id,
        title: `KR ${i}`,
        targetValue: 100 * i,
        baselineValue: 0,
        scoringType: "LINEAR_INCREASE",
        unit: "count",
        authorization: ws.bearerToken,
      });
    }

    await expect(
      addKeyResultService({
        objectiveId: objWith4Krs.id,
        title: "KR 4",
        targetValue: 400,
        baselineValue: 0,
        scoringType: "LINEAR_INCREASE",
        unit: "count",
        authorization: ws.bearerToken,
      })
    ).rejects.toThrow("maximum of 3 Key Results");
  });

  it("rejects cross-workspace Key Result links when creating an Initiative", async () => {
    const ws1 = await createTestWorkspaceWithMember({ role: "founder" });
    const ws2 = await createTestWorkspaceWithMember({ role: "founder" });

    const cycle1 = await createOkrCycleService({
      workspaceId: ws1.workspaceId,
      name: "Chu kỳ Workspace 1",
      authorization: ws1.bearerToken,
    });

    const obj1 = await createObjectiveService({
      workspaceId: ws1.workspaceId,
      cycleId: cycle1.id,
      title: "Objective Workspace 1",
      authorization: ws1.bearerToken,
    });

    const kr1 = await addKeyResultService({
      objectiveId: obj1.id,
      title: "KR Workspace 1",
      targetValue: 100,
      baselineValue: 0,
      unit: "count",
      authorization: ws1.bearerToken,
    });

    // Attempt to link kr1 in an initiative belonging to workspace 2
    await expect(
      createInitiativeService(
        {
          workspaceId: ws2.workspaceId,
          title: "Sáng kiến Workspace 2 cố gắn KR Workspace 1",
          keyResultIds: [kr1.id],
        },
        ws2.bearerToken
      )
    ).rejects.toThrow("do not belong to caller workspace");
  });

  it("enforces strategy.initiative.approve governance authority and creates audit decision record", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const founderCtx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    const init = await createInitiativeService(
      {
        workspaceId: ws.workspaceId,
        title: "Chiến dịch tiếp thị số đa kênh",
        description: "Mở rộng tiếp cận 100k người dùng",
        intendedOutcome: "Tăng 50% lượng lead inbound",
      },
      ws.bearerToken
    );
    expect(init.approvalStatus).toBe("DRAFT");

    // Non-founder member attempts approval under FOUNDER_ONLY -> Denied
    const memberCtx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: "non-founder-user",
      membershipRole: "member",
      permissions: ["strategy.write"],
    });

    await expect(
      approveInitiativeService({ id: init.id }, memberCtx)
    ).rejects.toThrow();

    // Founder approves -> Succeeds
    const approved = await approveInitiativeService(
      { id: init.id, reason: "Phê duyệt ngân sách chiến dịch Q1" },
      founderCtx
    );

    expect(approved.approvalStatus).toBe("APPROVED");
    expect(approved.approvedAt).toBeDefined();
    expect(approved.approvedByMemberId).toBeDefined();
    expect(approved.decisionId).toBeDefined();

    // Verify decision record in database
    const [decRow] = await db
      .select()
      .from(decisionRecords)
      .where(eq(decisionRecords.id, BigInt(approved.decisionId!)))
      .limit(1);

    expect(decRow).toBeDefined();
    expect(decRow.decision).toBe("INITIATIVE_APPROVED");
    expect(decRow.decisionType).toBe("INITIATIVE_APPROVAL");
  });

  it("supports nullable legacy reads and returns linked Key Result IDs in initiative response", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    const cycle = await createOkrCycleService({
      workspaceId: ws.workspaceId,
      name: "Chu kỳ Thường",
      authorization: ws.bearerToken,
    });

    // 1. Create legacy objective without strategicObjectiveId or towsOptionId
    const legacyObj = await createObjectiveService({
      workspaceId: ws.workspaceId,
      cycleId: cycle.id,
      title: "Mục tiêu BAU kế thừa",
      authorization: ws.bearerToken,
    });

    expect(legacyObj.strategicObjectiveId).toBeNull();
    expect(legacyObj.towsOptionId).toBeNull();

    const loadedObj = await getObjectiveService(legacyObj.id, ws.bearerToken);
    expect(loadedObj.strategicObjectiveId).toBeNull();
    expect(loadedObj.towsOptionId).toBeNull();

    // 2. Add Key Results and link to Initiative
    const kr1 = await addKeyResultService({
      objectiveId: legacyObj.id,
      title: "Hoàn tất kiểm toán nội bộ",
      targetValue: 1,
      baselineValue: 0,
      unit: "report",
      authorization: ws.bearerToken,
    });

    const init = await createInitiativeService(
      {
        workspaceId: ws.workspaceId,
        title: "Sáng kiến nâng chuẩn quy trình",
        keyResultIds: [kr1.id],
      },
      ws.bearerToken
    );

    expect(init.keyResultIds).toEqual([kr1.id]);

    const loadedInit = await getInitiativeService(init.id, ws.bearerToken);
    expect(loadedInit.keyResultIds).toEqual([kr1.id]);
    expect(loadedInit.strategicObjectiveId).toBeNull();
    expect(loadedInit.sourceTowsOptionId).toBeNull();

    // 3. List initiatives
    const listed = await listInitiativesService(
      { workspaceId: ws.workspaceId },
      ctx
    );
    expect(listed.items.length).toBeGreaterThanOrEqual(1);
    const found = listed.items.find((i) => i.id === init.id);
    expect(found).toBeDefined();
    expect(found!.keyResultIds).toContain(kr1.id);
  });
});
