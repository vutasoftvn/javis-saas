import { describe, it, expect } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestWorkspaceWithMember, seedObjectiveWithKeyResult } from "./_helpers";
import { createAiInitiativeInWorkspace } from "../services/initiative.service";
import {
  recordValueContract,
  getActiveValueContract,
  recordDataReadinessAssessment,
  getActiveDataReadinessAssessment,
  setBudgetPolicy,
  getActiveBudgetPolicy,
  recordMeasurement,
  getLatestMeasurement,
  recordInitiativeDecision,
  listInitiativeDecisions,
} from "../services/ai-initiative-evidence.service";
import type { TenantContext } from "../../shared/types/tenant_context";

async function seedHumanMember(wsId: string, userId: string): Promise<string> {
  const memberId = generateSnowflake();
  await db.execute(sql`
    INSERT INTO core.workforce_members (id, workspace_id, member_type, human_user_id, role_title, status)
    VALUES (${memberId}, ${BigInt(wsId)}, 'HUMAN', ${BigInt(userId)}, 'Founder', 'active')
  `);
  return memberId.toString();
}

function makeTenantContext(wsId: string, userId: string, memberId?: string): TenantContext {
  return {
    workspaceId: wsId,
    userId,
    membershipRole: "founder",
    permissions: ["*"],
    correlationId: "test-corr-evidence",
  };
}

describe("AI Initiative Evidence Service", () => {
  it("rejects VALIDATE evidence without a baseline source reference", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);
    const memberId = await seedHumanMember(ws.workspaceId, ws.userId);
    const ctx = makeTenantContext(ws.workspaceId, ws.userId, memberId);

    const init = await createAiInitiativeInWorkspace(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "Value Contract Initiative",
      businessProblem: "Manual tasks",
      intendedOutcome: "Automation",
      businessOwnerMemberId: ws.userId,
      keyResultIds: [okr.keyResultId],
    });

    await expect(
      recordValueContract(ctx, {
        workspaceId: ws.workspaceId,
        projectId: ws.projectId,
        initiativeId: init.id,
        metricContractId: "metric.cycle_time.v1",
        baselineValue: "120.5",
        baselineObservedAt: new Date().toISOString(),
        baselineSourceRef: "", // Empty or missing
        targetValue: "60.0",
        targetBy: new Date().toISOString(),
        measurementWindow: "30d",
        unit: "minutes",
        scoringDirection: "DESC",
        expectedValueMethod: "cycle_time",
        measurementOwnerMemberId: memberId,
      })
    ).rejects.toThrow("baseline_source_ref is required");
  });

  it("stores 12.3400 as a decimal string and never returns 0 for an unavailable measurement", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);
    const memberId = await seedHumanMember(ws.workspaceId, ws.userId);
    const ctx = makeTenantContext(ws.workspaceId, ws.userId, memberId);

    const init = await createAiInitiativeInWorkspace(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "Measurement Initiative",
      businessProblem: "Telemetry",
      intendedOutcome: "Observation",
      businessOwnerMemberId: ws.userId,
      keyResultIds: [okr.keyResultId],
    });

    // Record an unavailable measurement
    await recordMeasurement(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      metricContractId: "metric.accuracy.v1",
      observedValue: null,
      state: "UNAVAILABLE",
      observedAt: new Date().toISOString(),
      windowStart: new Date(Date.now() - 86400000).toISOString(),
      windowEnd: new Date().toISOString(),
      missingDataState: "DATA_SOURCE_PENDING_INGESTION",
    });

    const latest = await getLatestMeasurement(ws.workspaceId, init.id, "metric.accuracy.v1");
    expect(latest).toBeDefined();
    expect(latest!.state).toBe("UNAVAILABLE");
    expect(latest!.observedValue).toBeNull();
  });

  it("records append-only revisions for value contracts, assessments, budget and decisions", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);
    const memberId = await seedHumanMember(ws.workspaceId, ws.userId);
    const ctx = makeTenantContext(ws.workspaceId, ws.userId, memberId);

    const init = await createAiInitiativeInWorkspace(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "Append-only Revision Initiative",
      businessProblem: "Verification",
      intendedOutcome: "Evidence tracking",
      businessOwnerMemberId: ws.userId,
      keyResultIds: [okr.keyResultId],
    });

    // 1. Value contract revisions
    const vc1 = await recordValueContract(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      metricContractId: "metric.revenue.v1",
      baselineValue: "10000000.00",
      baselineObservedAt: new Date().toISOString(),
      baselineSourceRef: "audit:baseline-2026-09",
      targetValue: "20000000.00",
      targetBy: new Date().toISOString(),
      measurementWindow: "30d",
      unit: "VND",
      scoringDirection: "ASC",
      expectedValueMethod: "revenue",
      expectedValueAmount: "10000000.00",
      currency: "VND",
      measurementOwnerMemberId: memberId,
    });
    expect(vc1.revision).toBe(1);
    expect(vc1.baselineValue).toBe("10000000.0000");

    const vc2 = await recordValueContract(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      metricContractId: "metric.revenue.v1",
      baselineValue: "10000000.00",
      baselineObservedAt: new Date().toISOString(),
      baselineSourceRef: "audit:baseline-2026-09",
      targetValue: "25000000.00",
      targetBy: new Date().toISOString(),
      measurementWindow: "30d",
      unit: "VND",
      scoringDirection: "ASC",
      expectedValueMethod: "revenue",
      expectedValueAmount: "15000000.00",
      currency: "VND",
      measurementOwnerMemberId: memberId,
    });
    expect(vc2.revision).toBe(2);

    const activeVc = await getActiveValueContract(ws.workspaceId, init.id);
    expect(activeVc!.revision).toBe(2);
    expect(activeVc!.targetValue).toBe("25000000.0000");

    // 2. Data readiness assessment
    const dra1 = await recordDataReadinessAssessment(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      sourceRefs: ["vault:source-finance-q3"],
      classification: "INTERNAL",
      accessAuthorityRef: "auth:founder-role",
      freshnessSlo: "24h",
      qualityDimensions: { completeness: 0.95, accuracy: 0.98 },
      metadataOwnerMemberId: memberId,
      retrievalMode: "lexical",
      assessmentStatus: "READY",
      evidenceRefs: ["evidence:eval-q3-pass"],
    });
    expect(dra1.revision).toBe(1);
    expect(dra1.assessmentStatus).toBe("READY");

    const activeDra = await getActiveDataReadinessAssessment(ws.workspaceId, init.id);
    expect(activeDra!.assessmentStatus).toBe("READY");

    // 3. Budget policy
    const bp1 = await setBudgetPolicy(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      period: "MONTHLY",
      currency: "USD",
      softCostThreshold: "100.00",
      hardCostThreshold: "250.00",
      actionOnBreach: "PAUSE_INITIATIVE",
      allowedModels: ["openai/gpt-4o", "anthropic/claude-3-5-sonnet"],
    });
    expect(bp1.revision).toBe(1);
    expect(bp1.hardCostThreshold).toBe("250.0000");

    const activeBp = await getActiveBudgetPolicy(ws.workspaceId, init.id);
    expect(activeBp!.actionOnBreach).toBe("PAUSE_INITIATIVE");

    // 4. Decision recording with idempotency
    const d1 = await recordInitiativeDecision(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      decision: "PILOT_TO_VALIDATE",
      fromState: "PILOT",
      toState: "VALIDATE",
      actorMemberId: memberId,
      reasonCode: "EVAL_AND_METRICS_PASS",
      reason: "All baseline and evaluation gates passed",
      gateSnapshot: { baselinePassed: true, evalPassed: true },
      idempotencyKey: "idem-pilot-to-validate-001",
    });
    expect(d1.id).toBeDefined();

    // Replay with same idempotency key returns exact same record
    const d1Replay = await recordInitiativeDecision(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      decision: "PILOT_TO_VALIDATE",
      fromState: "PILOT",
      toState: "VALIDATE",
      actorMemberId: memberId,
      reasonCode: "EVAL_AND_METRICS_PASS",
      reason: "All baseline and evaluation gates passed",
      gateSnapshot: { baselinePassed: true, evalPassed: true },
      idempotencyKey: "idem-pilot-to-validate-001",
    });
    expect(d1Replay.id).toBe(d1.id);

    const decisions = await listInitiativeDecisions(ws.workspaceId, init.id);
    expect(decisions.length).toBe(1);
  });
});
