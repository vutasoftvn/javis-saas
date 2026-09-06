import { randomUUID } from "node:crypto";
import { describe, expect, it } from "vitest";
import { APIError } from "encore.dev/api";
import { createTestWorkspaceWithMember, addMemberToWorkspace } from "../../tests/_helpers";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import { db } from "../../models/db";
import { decisionRecords } from "../../../shared/db/schema/strategy";
import {
  coreWorkspaceRoles,
  coreRolePermissions,
  coreMemberRoleAssignments,
  identityWorkforceMembers,
} from "../../../shared/db/schema/identity";
import { eq } from "drizzle-orm";
import {
  createStrategicObjective,
  updateStrategicObjective,
} from "../services/strategic-objective.service";
import {
  createSwotItem,
  updateSwotItem,
} from "../services/strategy-analysis.service";
import {
  createTowsOption,
  createTowsOptionEvaluation,
  getTowsOption,
  listTowsOptions,
  selectTowsOption,
  rejectTowsOption,
  updateTowsOption,
  calculatePriorityScore,
} from "../services/tows-option.service";
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

describe("tows-option service", () => {
  it("calculates priority scores and automatically orders candidates without automatic selection", async () => {
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

    const obj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Mở rộng thị trường doanh nghiệp vừa và nhỏ",
      successDefinition: "Đạt 500 khách hàng trả phí trong 12 tháng",
      status: "ACTIVE",
    });

    // Create Option 1
    const opt1 = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "SO",
      title: "Chiến lược SO: Tích hợp AI vào sản phẩm hiện có",
      rationale: "Tận dụng thế mạnh công nghệ và cơ hội thị trường",
    });

    // Create Option 2
    const opt2 = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "WO",
      title: "Chiến lược WO: Hợp tác với đối tác phân phối B2B",
      rationale: "Khắc phục điểm yếu kênh bán hàng",
    });

    // Option 1 evaluation: impact 3, difficulty 4 -> priorityScore = 3 * 2 - 4 = 2
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: opt1.id,
      impactScore: 3,
      difficultyScore: 4,
      scorerKind: "HUMAN",
    });

    // Option 2 evaluation: impact 5, difficulty 2 -> priorityScore = 5 * 2 - 2 = 8
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: opt2.id,
      impactScore: 5,
      difficultyScore: 2,
      scorerKind: "AI_AGENT",
    });

    expect(calculatePriorityScore(3, 4)).toBe(2);
    expect(calculatePriorityScore(5, 2)).toBe(8);

    const listed = await listTowsOptions({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
    });

    expect(listed.items).toHaveLength(2);
    // Highest priority score must be first
    expect(listed.items[0].id).toBe(opt2.id);
    expect(listed.items[0].priorityScore).toBe(8);
    expect(listed.items[0].status).toBe("DRAFT"); // Not automatically selected!

    expect(listed.items[1].id).toBe(opt1.id);
    expect(listed.items[1].priorityScore).toBe(2);
    expect(listed.items[1].status).toBe("DRAFT"); // Not automatically selected!
  });

  it("enforces top-1 and top-2 selection limits according to workspace policy", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    // Set towsSelectionLimit to 1
    await updateWorkspaceStrategySettings(ctx, {
      workspaceId: ws.workspaceId,
      bscMode: "OFF",
      towsSelectionLimit: 1,
    });

    const obj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Thâm nhập thị trường Đông Nam Á",
      successDefinition: "Đạt 1 triệu USD ARR sau 1 năm",
      status: "ACTIVE",
    });

    const optA = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "SO",
      title: "Option A",
    });
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: optA.id,
      impactScore: 4,
      difficultyScore: 2,
    });

    const optB = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "ST",
      title: "Option B",
    });
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: optB.id,
      impactScore: 4,
      difficultyScore: 3,
    });

    // Select Option A -> Success under limit 1
    const selectedA = await selectTowsOption({ id: optA.id }, ctx);
    expect(selectedA.status).toBe("SELECTED");
    expect(selectedA.selectedAt).toBeDefined();

    // Try to select Option B -> Fails due to limit 1
    await expect(selectTowsOption({ id: optB.id }, ctx)).rejects.toThrow(
      "TOWS selection limit of 1 reached"
    );

    // Update settings to allow limit 2
    await updateWorkspaceStrategySettings(ctx, {
      workspaceId: ws.workspaceId,
      towsSelectionLimit: 2,
    });

    // Now select Option B -> Success under limit 2
    const selectedB = await selectTowsOption({ id: optB.id }, ctx);
    expect(selectedB.status).toBe("SELECTED");

    // Create Option C and try to select without supersede -> Fails due to limit 2
    const optC = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "WT",
      title: "Option C",
    });
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: optC.id,
      impactScore: 5,
      difficultyScore: 1,
    });

    await expect(selectTowsOption({ id: optC.id }, ctx)).rejects.toThrow(
      "TOWS selection limit of 2 reached"
    );
  });

  it("handles replacement selection by marking superseded option in same transaction and preserving audit history", async () => {
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
      towsSelectionLimit: 1,
    });

    const obj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Tối ưu hóa chi phí vận hành",
      successDefinition: "Giảm 30% chi phí cơ sở hạ tầng trong 6 tháng",
      status: "ACTIVE",
    });

    const opt1 = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "WO",
      title: "Tái cấu trúc cụm máy chủ tự lưu trữ",
    });
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: opt1.id,
      impactScore: 3,
      difficultyScore: 3,
    });

    await selectTowsOption({ id: opt1.id, reason: "Lựa chọn ban đầu" }, ctx);
    const loaded1 = await getTowsOption(opt1.id, ws.workspaceId);
    expect(loaded1.status).toBe("SELECTED");

    const opt2 = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "SO",
      title: "Chuyển đổi sang kiến trúc Serverless",
    });
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: opt2.id,
      impactScore: 5,
      difficultyScore: 2,
    });

    // Select opt2 superseding opt1
    const selected2 = await selectTowsOption(
      {
        id: opt2.id,
        reason: "Kiến trúc serverless mang lại ROI cao hơn đáng kể",
        supersedeOptionId: opt1.id,
      },
      ctx
    );

    expect(selected2.status).toBe("SELECTED");
    expect(selected2.decisionId).toBeDefined();

    // Verify opt1 is now SUPERSEDED
    const loadedSuperseded1 = await getTowsOption(opt1.id, ws.workspaceId);
    expect(loadedSuperseded1.status).toBe("SUPERSEDED");

    // Verify decision record in strategy.decision_records
    const [decRecord] = await db
      .select()
      .from(decisionRecords)
      .where(eq(decisionRecords.id, BigInt(selected2.decisionId!)))
      .limit(1);

    expect(decRecord).toBeDefined();
    expect(decRecord.decision).toBe("TOWS_OPTION_SELECTED");
    expect(decRecord.decisionType).toBe("TOWS_SELECTION");
    const snapshot = decRecord.evidenceSnapshot as any;
    expect(snapshot.supersededOptionId).toBe(opt1.id);
    expect(snapshot.selectedIds).toContain(opt2.id);
    expect(snapshot.reason).toContain("ROI cao hơn");
  });

  it("rejects selection when option has no evaluations or linked SWOT items are not active", async () => {
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

    const obj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Nâng cao trải nghiệm khách hàng",
      successDefinition: "NPS tăng từ 40 lên 70",
      status: "ACTIVE",
    });

    // 1. Option without evaluations -> rejected
    const unevaluated = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "SO",
      title: "Chưa đánh giá điểm",
    });

    await expect(selectTowsOption({ id: unevaluated.id }, ctx)).rejects.toThrow(
      "must have at least one evaluation"
    );

    // 2. Option with linked DRAFT SWOT item -> rejected
    const swotDraft = await createSwotItem(ctx, {
      strategicObjectiveId: obj.id,
      kind: "STRENGTH",
      statement: "Đội ngũ CSKH tận tâm",
      sourceType: "MANUAL",
      status: "DRAFT", // Still draft!
    });

    const optWithDraftSwot = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "SO",
      title: "Chiến lược gắn với SWOT nháp",
      swotItemIds: [swotDraft.id],
    });
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: optWithDraftSwot.id,
      impactScore: 4,
      difficultyScore: 2,
    });

    await expect(
      selectTowsOption({ id: optWithDraftSwot.id }, ctx)
    ).rejects.toThrow("must be ACTIVE");

    // Activate the SWOT item -> Selection now succeeds
    await updateSwotItem(ctx, {
      id: swotDraft.id,
      status: "ACTIVE",
    });

    const selectedNow = await selectTowsOption(
      { id: optWithDraftSwot.id },
      ctx
    );
    expect(selectedNow.status).toBe("SELECTED");
  });

  it("denies selection and rejection to AI agents", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const founderCtx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    await updateWorkspaceStrategySettings(founderCtx, {
      workspaceId: ws.workspaceId,
      bscMode: "OFF",
    });

    const obj = await createStrategicObjective(founderCtx, {
      workspaceId: ws.workspaceId,
      title: "Tự động hóa báo cáo tài chính",
      successDefinition: "Hoàn tất báo cáo trong 2 giờ thay vì 2 ngày",
      status: "ACTIVE",
    });

    const opt = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "SO",
      title: "Sử dụng Agent RPA",
    });
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: opt.id,
      impactScore: 4,
      difficultyScore: 2,
    });

    const agentCtx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: "agent-user",
      membershipRole: "agent",
      permissions: ["*"],
      // actorKind indicator
      ...({ actorKind: "AI_AGENT" } as any),
    });

    // Agent attempts selection -> Denied
    await expect(selectTowsOption({ id: opt.id }, agentCtx)).rejects.toThrow(
      "Agent cannot perform governance decisions"
    );

    // Agent attempts rejection -> Denied
    await expect(rejectTowsOption({ id: opt.id }, agentCtx)).rejects.toThrow(
      "Agent cannot perform governance decisions"
    );
  });

  it("handles delegated approver authority and rejection workflow", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const founderCtx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    // Set approval policy to DELEGATED_APPROVER
    await updateWorkspaceStrategySettings(founderCtx, {
      workspaceId: ws.workspaceId,
      approvalPolicy: "DELEGATED_APPROVER",
      bscMode: "OFF",
    });

    const obj = await createStrategicObjective(founderCtx, {
      workspaceId: ws.workspaceId,
      title: "Tối ưu hóa trải nghiệm nhân viên",
      successDefinition: "eNPS > 60",
      status: "ACTIVE",
    });

    const opt = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "WO",
      title: "Triển khai chính sách làm việc linh hoạt",
    });
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: opt.id,
      impactScore: 4,
      difficultyScore: 3,
    });

    // Setup workforce member with delegated strategy lead role
    const wsId = BigInt(ws.workspaceId);
    const delegatedUser = await addMemberToWorkspace(ws.workspaceId, "member");
    const workforceMemberId = generateSnowflake();

    await db.insert(identityWorkforceMembers).values({
      id: workforceMemberId,
      workspaceId: wsId,
      memberType: "HUMAN",
      humanUserId: BigInt(delegatedUser.userId),
      roleTitle: "Strategy Officer",
      status: "active",
    });

    const roleId = randomUUID();
    await db.insert(coreWorkspaceRoles).values({
      id: roleId,
      workspaceId: wsId,
      roleKey: "strategy_option_lead",
      name: "Strategy Option Lead",
      isSystem: false,
    });

    await db.insert(coreRolePermissions).values({
      roleId,
      permissionKey: "strategy.option.select",
      effect: "ALLOW",
      conditions: {},
    });

    await db.insert(coreMemberRoleAssignments).values({
      id: randomUUID(),
      workspaceId: wsId,
      workforceMemberId,
      roleId,
    });

    // Context without strategy.option.select permission -> Fails
    const nonGranteeCtx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: "team-lead-1",
      membershipRole: "member",
      permissions: ["strategy.read"],
    });
    await expect(selectTowsOption({ id: opt.id }, nonGranteeCtx)).rejects.toThrow();

    // Context with delegated role assignment and workforceMemberId -> Succeeds
    const delegatedCtx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: delegatedUser.userId,
      workforceMemberId: workforceMemberId.toString(),
      membershipRole: "member",
      permissions: ["strategy.option.select"],
    });
    const selected = await selectTowsOption(
      { id: opt.id, reason: "Phù hợp văn hóa công ty" },
      delegatedCtx
    );
    expect(selected.status).toBe("SELECTED");

    // Now test reject on another option
    const optToReject = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "WT",
      title: "Cắt giảm toàn bộ chi phí đào tạo",
    });

    const rejected = await rejectTowsOption(
      { id: optToReject.id, reason: "Ảnh hưởng xấu đến chất lượng nhân sự" },
      delegatedCtx
    );
    expect(rejected.status).toBe("REJECTED");
    expect(rejected.decisionId).toBeDefined();

  });

  it("handles concurrent selection collision without exceeding limits", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    // Set limit = 1
    await updateWorkspaceStrategySettings(ctx, {
      workspaceId: ws.workspaceId,
      bscMode: "OFF",
      towsSelectionLimit: 1,
    });

    const obj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Mục tiêu đua tranh tài nguyên",
      successDefinition: "Thử nghiệm concurrency limit 1",
      status: "ACTIVE",
    });

    const optA = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "SO",
      title: "Ứng viên A",
    });
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: optA.id,
      impactScore: 4,
      difficultyScore: 2,
    });

    const optB = await createTowsOption({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      quadrant: "WO",
      title: "Ứng viên B",
    });
    await createTowsOptionEvaluation({
      workspaceId: ws.workspaceId,
      towsOptionId: optB.id,
      impactScore: 4,
      difficultyScore: 2,
    });

    // Fire two select requests concurrently
    const results = await Promise.allSettled([
      selectTowsOption({ id: optA.id }, ctx),
      selectTowsOption({ id: optB.id }, ctx),
    ]);

    const fulfilled = results.filter((r) => r.status === "fulfilled");
    const rejected = results.filter((r) => r.status === "rejected");

    // Exactly 1 must be fulfilled, exactly 1 rejected due to limit 1 and database row lock
    expect(fulfilled).toHaveLength(1);
    expect(rejected).toHaveLength(1);

    // Verify in database that exactly 1 option is SELECTED
    const listed = await listTowsOptions({
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      status: "SELECTED",
    });
    expect(listed.items).toHaveLength(1);
  });
});
