import { describe, it, expect } from "vitest";
import { sql, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestWorkspaceWithMember, seedObjectiveWithKeyResult } from "./_helpers";
import {
  createAiInitiativeInWorkspace,
} from "../services/initiative.service";
import {
  recordValueContract,
  recordDataReadinessAssessment,
} from "../services/ai-initiative-evidence.service";
import {
  transitionAiInitiative,
} from "../services/ai-initiative-transition.service";
import {
  evaluateAiInitiativePromotionGates,
} from "../services/ai-initiative-promotion-policy";
import type { TenantContext } from "../../shared/types/tenant_context";

const { initiatives } = schema;

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
    workforceMemberId: memberId,
    membershipRole: "founder",
    permissions: ["*"],
    correlationId: "test-corr-transition",
  };
}

describe("AI Initiative Promotion Policy (Pure)", () => {
  it("requires APPROVED status for DISCOVER -> PILOT", () => {
    const gates = evaluateAiInitiativePromotionGates({
      fromState: "DISCOVER",
      toState: "PILOT",
      riskTier: "LOW",
      autonomyTier: "A0",
      approvalStatus: "DRAFT",
      hasOwner: true,
      hasProblemStatement: true,
      hasIntendedOutcome: true,
    });
    expect(gates).toContain("APPROVAL_STATUS_REQUIRED");
  });

  it("blocks A3 autonomy tier as unsupported", () => {
    const gates = evaluateAiInitiativePromotionGates({
      fromState: "DISCOVER",
      toState: "PILOT",
      riskTier: "HIGH",
      autonomyTier: "A3",
      approvalStatus: "APPROVED",
      hasOwner: true,
      hasProblemStatement: true,
      hasIntendedOutcome: true,
    });
    expect(gates).toContain("UNSUPPORTED_AUTONOMY_TIER");
  });

  it("requires baseline, metric, owner, and data assessment for PILOT -> VALIDATE", () => {
    const gates = evaluateAiInitiativePromotionGates({
      fromState: "PILOT",
      toState: "VALIDATE",
      riskTier: "MEDIUM",
      autonomyTier: "A1",
      approvalStatus: "APPROVED",
      hasOwner: false,
      hasValueContract: false,
      hasBaseline: false,
      hasDataAssessment: false,
    });
    expect(gates).toContain("BASELINE_AND_METRIC_REQUIRED");
    expect(gates).toContain("OWNER_REQUIRED");
    expect(gates).toContain("DATA_READINESS_ASSESSMENT_REQUIRED");
  });
});

describe("AI Initiative Transition Service", () => {
  it("rejects DISCOVER to PILOT when approvalStatus is not APPROVED", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);
    const memberId = await seedHumanMember(ws.workspaceId, ws.userId);
    const ctx = makeTenantContext(ws.workspaceId, ws.userId, memberId);

    const init = await createAiInitiativeInWorkspace(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "Draft Initiative",
      businessProblem: "Inefficient manual workflows",
      intendedOutcome: "Faster completion",
      businessOwnerMemberId: ws.userId,
      keyResultIds: [okr.keyResultId],
    });

    const discoverToPilotWithDraftApproval = {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      targetState: "PILOT" as const,
      expectedRevision: init.revision,
      reasonCode: "START_PILOT",
    };

    await expect(
      transitionAiInitiative(discoverToPilotWithDraftApproval, ctx)
    ).rejects.toThrow("approvalStatus must be APPROVED");
  });

  it("rejects cross-Project evidence and a stale expectedRevision", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);
    const memberId = await seedHumanMember(ws.workspaceId, ws.userId);
    const ctx = makeTenantContext(ws.workspaceId, ws.userId, memberId);

    const init = await createAiInitiativeInWorkspace(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "Conflict Initiative",
      businessProblem: "Problem",
      intendedOutcome: "Outcome",
      businessOwnerMemberId: ws.userId,
      keyResultIds: [okr.keyResultId],
    });

    const staleOrForeignEvidence = {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      targetState: "PILOT" as const,
      expectedRevision: 999, // Stale revision
      reasonCode: "START_PILOT",
    };

    await expect(
      transitionAiInitiative(staleOrForeignEvidence, ctx)
    ).rejects.toThrow("Revision conflict");

    // Also verify cross-project mismatch
    const foreignProjectTransition = {
      workspaceId: ws.workspaceId,
      projectId: "9999999999999999",
      initiativeId: init.id,
      targetState: "PILOT" as const,
      expectedRevision: init.revision,
      reasonCode: "START_PILOT",
    };
    await expect(
      transitionAiInitiative(foreignProjectTransition, ctx)
    ).rejects.toThrow("Project does not match initiative project");
  });

  it("allows PILOT to VALIDATE only with baseline, metric, owner, risk and data assessment", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);
    const memberId = await seedHumanMember(ws.workspaceId, ws.userId);
    const ctx = makeTenantContext(ws.workspaceId, ws.userId, memberId);

    const init = await createAiInitiativeInWorkspace(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "Full Lifecycle Initiative",
      businessProblem: "Manual data entry",
      intendedOutcome: "Automated entry with 95% accuracy",
      businessOwnerMemberId: ws.userId,
      keyResultIds: [okr.keyResultId],
    });

    // Mark as APPROVED and transition to PILOT
    await db
      .update(initiatives)
      .set({ approvalStatus: "APPROVED" })
      .where(eq(initiatives.id, BigInt(init.id)));

    const pilotResult = await transitionAiInitiative(
      {
        workspaceId: ws.workspaceId,
        projectId: ws.projectId,
        initiativeId: init.id,
        targetState: "PILOT",
        expectedRevision: init.revision,
        reasonCode: "PILOT_APPROVED",
      },
      ctx
    );

    expect(pilotResult.currentState).toBe("PILOT");

    // Attempt PILOT -> VALIDATE without evidence: must fail
    await expect(
      transitionAiInitiative(
        {
          workspaceId: ws.workspaceId,
          projectId: ws.projectId,
          initiativeId: init.id,
          targetState: "VALIDATE",
          expectedRevision: pilotResult.initiative.revision,
          reasonCode: "EVALUATE_PILOT",
        },
        ctx
      )
    ).rejects.toThrow("Promotion gates failed");

    // Attach required evidence: Value Contract with baseline + Data Readiness Assessment
    await recordValueContract(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      metricContractId: "cycle-time-contract",
      unit: "HOURS",
      baselineValue: "40.0",
      targetValue: "10.0",
      baselineSourceRef: "timesheet-export-2026.csv",
      measurementOwnerMemberId: memberId,
    });

    await recordDataReadinessAssessment(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      assessmentStatus: "READY",
      classification: "CONFIDENTIAL",
      metadataOwnerMemberId: memberId,
    });

    // Now transition to VALIDATE should succeed
    const validPilotToValidate = {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      targetState: "VALIDATE" as const,
      expectedRevision: pilotResult.initiative.revision,
      reasonCode: "PILOT_VALIDATED",
    };

    await expect(
      transitionAiInitiative(validPilotToValidate, ctx)
    ).resolves.toMatchObject({ lifecycleState: "VALIDATE" });
  });
});
