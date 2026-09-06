import { describe, expect, it } from "vitest";
import { APIError } from "encore.dev/api";
import { createTestWorkspaceWithMember } from "../../tests/_helpers";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import { db } from "../../models/db";
import { identityWorkforceMembers } from "../../../shared/db/schema/identity";
import {
  createStrategicObjective,
  saveBscFocusScopes,
} from "../services/strategic-objective.service";
import { updateWorkspaceStrategySettings } from "../services/workspace-strategy-settings.service";
import {
  createPestelSignal,
  listPestelSignals,
  createResourceCapabilityAssessment,
  listResourceCapabilityAssessments,
  createSwotItem,
  listSwotItems,
  updateSwotItem,
  deriveSwotDrafts,
} from "../services/strategy-analysis.service";

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

describe("strategy-analysis service", () => {
  it("enforces active objective precondition for analysis artefacts", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    // Create DRAFT objective
    const draftObj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Mục tiêu bản nháp",
    });

    // Attempt to create PESTEL signal on DRAFT objective -> fails
    await expect(
      createPestelSignal(ctx, {
        strategicObjectiveId: draftObj.id,
        dimension: "TECHNOLOGICAL",
        statement: "Sự bùng nổ của AI Agent",
        impact: "HIGH",
        certainty: "HIGH",
      })
    ).rejects.toThrow("must be ACTIVE");

    // Attempt to list on DRAFT objective -> fails
    await expect(
      listPestelSignals(ctx, draftObj.id)
    ).rejects.toThrow("must be ACTIVE");
  });

  it("validates enums for PESTEL, Resource categories, and SWOT kinds", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    const activeObj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Mục tiêu số hóa",
      successDefinition: "Chuyển đổi 100% quy trình lên cloud trước 2027",
      status: "ACTIVE",
    });

    // Invalid PESTEL dimension
    await expect(
      createPestelSignal(ctx, {
        strategicObjectiveId: activeObj.id,
        dimension: "INVALID_DIMENSION" as any,
        statement: "Thị trường biến động",
        impact: "HIGH",
        certainty: "HIGH",
      })
    ).rejects.toThrow("Invalid PESTEL dimension");

    // Invalid Resource category
    await expect(
      createResourceCapabilityAssessment(ctx, {
        strategicObjectiveId: activeObj.id,
        category: "TAI_NHAN_TRI_VAT" as any,
        statement: "Tài chính dồi dào",
        strengthLevel: "STRONG",
      })
    ).rejects.toThrow("Invalid resource category");

    // Invalid SWOT kind
    await expect(
      createSwotItem(ctx, {
        strategicObjectiveId: activeObj.id,
        kind: "ADVANTAGE" as any,
        statement: "Ưu thế cạnh tranh",
        sourceType: "MANUAL",
      })
    ).rejects.toThrow("Invalid SWOT kind");
  });

  it("enforces BSC required intersection validation", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    // Configure workspace with REQUIRED mode
    await updateWorkspaceStrategySettings(ctx, {
      workspaceId: ws.workspaceId,
      strategyMethod: "BSC_FILTER",
      bscMode: "REQUIRED",
      enabledBscPerspectives: ["FINANCIAL", "CUSTOMER"],
    });

    const obj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Tăng trưởng doanh thu B2B",
      successDefinition: "Đạt mốc 50 tỷ VND ARR",
    });

    // Add scope for FINANCIAL only
    await saveBscFocusScopes(ctx, {
      workspaceId: ws.workspaceId,
      strategicObjectiveId: obj.id,
      scopes: [
        {
          perspective: "FINANCIAL",
          focusStatement: "Tập trung hiệu quả biên lợi nhuận ròng",
        },
      ],
    });

    // Activate objective
    await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Active Obj",
      successDefinition: "Active success state",
      status: "ACTIVE",
    }).catch(() => {}); // ignore

    // Activate the first obj
    const { updateStrategicObjective } = await import("../services/strategic-objective.service");
    await updateStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      id: obj.id,
      status: "ACTIVE",
    });

    // Reject creating PESTEL with no intersection (empty perspectives)
    await expect(
      createPestelSignal(ctx, {
        strategicObjectiveId: obj.id,
        dimension: "ECONOMIC",
        statement: "Lãi suất ngân hàng hạ nhiệt",
        impact: "POSITIVE",
        certainty: "MEDIUM",
        bscPerspectives: [],
      })
    ).rejects.toThrow("must have at least one BSC perspective intersecting active focus scopes");

    // Reject creating PESTEL with perspective not in active focus scopes (e.g. CUSTOMER when active scope is only FINANCIAL)
    await expect(
      createPestelSignal(ctx, {
        strategicObjectiveId: obj.id,
        dimension: "ECONOMIC",
        statement: "Lãi suất ngân hàng hạ nhiệt",
        impact: "POSITIVE",
        certainty: "MEDIUM",
        bscPerspectives: ["CUSTOMER"],
      })
    ).rejects.toThrow("must have at least one BSC perspective intersecting active focus scopes");

    // Allow with intersecting perspective FINANCIAL
    const signal = await createPestelSignal(ctx, {
      strategicObjectiveId: obj.id,
      dimension: "ECONOMIC",
      statement: "Lãi suất ngân hàng hạ nhiệt",
      impact: "POSITIVE",
      certainty: "MEDIUM",
      bscPerspectives: ["FINANCIAL"],
      status: "ACTIVE",
    });
    expect(signal.id).toBeDefined();
    expect(signal.bscPerspectives).toEqual(["FINANCIAL"]);

    // BSC is a write-time filter. Once an artefact has passed that filter,
    // reads and SWOT derivation must remain available in REQUIRED mode.
    await expect(listPestelSignals(ctx, obj.id)).resolves.toMatchObject({
      items: [expect.objectContaining({ id: signal.id })],
    });
    await expect(listResourceCapabilityAssessments(ctx, obj.id)).resolves.toEqual({
      items: [],
    });
    await expect(listSwotItems(ctx, obj.id)).resolves.toEqual({ items: [] });
    await expect(deriveSwotDrafts(ctx, obj.id)).resolves.toMatchObject({
      items: [expect.objectContaining({ sourceId: signal.id })],
    });
  });

  it("preserves source-to-SWOT provenance and derives DRAFT SWOT items", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const ctx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    const activeObj = await createStrategicObjective(ctx, {
      workspaceId: ws.workspaceId,
      title: "Mục tiêu mở rộng quốc tế",
      successDefinition: "Có 50 khách hàng tại thị trường Singapore",
      status: "ACTIVE",
    });

    // Create active PESTEL signal
    const signal = await createPestelSignal(ctx, {
      strategicObjectiveId: activeObj.id,
      dimension: "TECHNOLOGICAL",
      statement: "Singapore đẩy mạnh trợ cấp hạ tầng AI",
      impact: "POSITIVE",
      certainty: "HIGH",
      evidenceRefs: ["ev-sg-001"],
      status: "ACTIVE",
    });

    // Create active Resource assessment
    const assessment = await createResourceCapabilityAssessment(ctx, {
      strategicObjectiveId: activeObj.id,
      category: "MARKET_RELATIONSHIP_ASSET",
      statement: "Đã có quan hệ chặt chẽ với đối tác Singapore Fintech Association",
      strengthLevel: "STRONG",
      evidenceRefs: ["ev-partner-002"],
      status: "ACTIVE",
    });

    // Manual SWOT creation with source provenance
    const manualSwot = await createSwotItem(ctx, {
      strategicObjectiveId: activeObj.id,
      kind: "OPPORTUNITY",
      statement: "Tận dụng trợ cấp chính phủ Singapore",
      sourceType: "PESTEL_SIGNAL",
      sourceId: signal.id,
      evidenceRefs: ["ev-sg-001"],
      status: "ACTIVE",
    });

    expect(manualSwot.sourceType).toBe("PESTEL_SIGNAL");
    expect(manualSwot.sourceId).toBe(signal.id);
    expect(manualSwot.evidenceRefs).toEqual(["ev-sg-001"]);

    // Derive SWOT drafts via AI helper
    const drafts = await deriveSwotDrafts(ctx, activeObj.id);
    expect(drafts.items.length).toBe(2);

    const oppDraft = drafts.items.find((i) => i.kind === "OPPORTUNITY");
    expect(oppDraft).toBeDefined();
    expect(oppDraft?.sourceType).toBe("PESTEL_SIGNAL");
    expect(oppDraft?.sourceId).toBe(signal.id);
    expect(oppDraft?.status).toBe("DRAFT"); // Strictly DRAFT!
    expect(oppDraft?.evidenceRefs).toEqual(["ev-sg-001"]);

    const strDraft = drafts.items.find((i) => i.kind === "STRENGTH");
    expect(strDraft).toBeDefined();
    expect(strDraft?.sourceType).toBe("RESOURCE_CAPABILITY");
    expect(strDraft?.sourceId).toBe(assessment.id);
    expect(strDraft?.status).toBe("DRAFT"); // Strictly DRAFT!
    expect(strDraft?.evidenceRefs).toEqual(["ev-partner-002"]);
  });

  it("prevents AI agent from directly activating a SWOT item without human write call", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    const wsId = BigInt(ws.workspaceId);
    const aiMemberId = generateSnowflake();

    // Create AI_AGENT workforce member
    await db.insert(identityWorkforceMembers).values({
      id: aiMemberId,
      workspaceId: wsId,
      memberType: "AI_AGENT",
      agentSpecId: "cosa.agents.strategy",
      agentSpecVersion: "1.0.0",
      roleTitle: "AI Strategy Copilot",
      status: "active",
    });

    const aiCtx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: aiMemberId.toString(),
      membershipRole: "member",
      permissions: ["*"],
    });

    const activeObj = await createStrategicObjective(aiCtx, {
      workspaceId: ws.workspaceId,
      title: "Mục tiêu tự động",
      successDefinition: "Đạt thành công",
      status: "ACTIVE",
    });

    // AI agent creating DRAFT SWOT item succeeds
    const draftItem = await createSwotItem(aiCtx, {
      strategicObjectiveId: activeObj.id,
      kind: "OPPORTUNITY",
      statement: "Cơ hội do AI phát hiện",
      sourceType: "MANUAL",
      status: "DRAFT",
    });
    expect(draftItem.status).toBe("DRAFT");

    // AI agent attempting to create directly as ACTIVE -> REJECTED
    await expect(
      createSwotItem(aiCtx, {
        strategicObjectiveId: activeObj.id,
        kind: "OPPORTUNITY",
        statement: "Cơ hội do AI cố tình kích hoạt",
        sourceType: "MANUAL",
        status: "ACTIVE",
      })
    ).rejects.toThrow("AI agents cannot activate SWOT items");

    // AI agent attempting to update DRAFT to ACTIVE -> REJECTED
    await expect(
      updateSwotItem(aiCtx, {
        id: draftItem.id,
        status: "ACTIVE",
      })
    ).rejects.toThrow("AI agents cannot activate SWOT items");

    // Human founder can activate the item
    const humanCtx = createMockTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    const activated = await updateSwotItem(humanCtx, {
      id: draftItem.id,
      status: "ACTIVE",
    });
    expect(activated.status).toBe("ACTIVE");
  });

  it("enforces workspace isolation for analysis artefacts and source provenance", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "founder" });
    const wsB = await createTestWorkspaceWithMember({ role: "founder" });

    const ctxA = createMockTenantContext({
      workspaceId: wsA.workspaceId,
      userId: wsA.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });
    const ctxB = createMockTenantContext({
      workspaceId: wsB.workspaceId,
      userId: wsB.userId,
      membershipRole: "founder",
      permissions: ["*"],
    });

    const objA = await createStrategicObjective(ctxA, {
      workspaceId: wsA.workspaceId,
      title: "Mục tiêu Workspace A",
      successDefinition: "Thành công A",
      status: "ACTIVE",
    });

    const objB = await createStrategicObjective(ctxB, {
      workspaceId: wsB.workspaceId,
      title: "Mục tiêu Workspace B",
      successDefinition: "Thành công B",
      status: "ACTIVE",
    });

    const signalB = await createPestelSignal(ctxB, {
      strategicObjectiveId: objB.id,
      dimension: "POLITICAL",
      statement: "Tín hiệu B",
      impact: "HIGH",
      certainty: "HIGH",
      status: "ACTIVE",
    });

    // Workspace A attempting to create SWOT linking to signal from Workspace B -> REJECTED
    await expect(
      createSwotItem(ctxA, {
        strategicObjectiveId: objA.id,
        kind: "OPPORTUNITY",
        statement: "Đánh cắp cơ hội từ Workspace B",
        sourceType: "PESTEL_SIGNAL",
        sourceId: signalB.id,
      })
    ).rejects.toThrow("Source PESTEL signal");

    // Workspace A attempting to list signals for Workspace B's objective -> REJECTED
    await expect(
      listPestelSignals(ctxA, objB.id)
    ).rejects.toThrow("not found in workspace");
  });
});
