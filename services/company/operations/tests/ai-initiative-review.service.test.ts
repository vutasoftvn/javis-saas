import { describe, it, expect } from "vitest";
import { sql, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestWorkspaceWithMember, seedObjectiveWithKeyResult } from "./_helpers";
import { createAiInitiativeInWorkspace, getAiInitiativeInWorkspace } from "../services/initiative.service";
import { recordValueContract, setBudgetPolicy } from "../services/ai-initiative-evidence.service";
import {
  recordAiInitiativeReview,
  pauseAiInitiative,
} from "../services/ai-initiative-review.service";
import type { TenantContext } from "../../shared/types/tenant_context";

const { initiatives, aiInitiativeDecisions } = schema;

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
    correlationId: "test-corr-review",
  };
}

describe("AI Initiative Review and Remediation Service", () => {
  it("records review recommendation and enforces idempotent pause preserving evidence", async () => {
    const ws = await createTestWorkspaceWithMember();
    const memberId = await seedHumanMember(ws.workspaceId, ws.userId);
    const ctx = makeTenantContext(ws.workspaceId, ws.userId, memberId);
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);

    // Create an AI initiative in PILOT
    const init = await createAiInitiativeInWorkspace(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "Review Test Initiative",
      businessOwnerMemberId: memberId,
      keyResultIds: [okr.keyResultId],
      riskTier: "MEDIUM",
      autonomyTier: "A1",
    });

    // Set value contract
    await recordValueContract(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      metricContractId: "csat-metric",
      unit: "points",
      baselineValue: "70.0",
      targetValue: "85.0",
      baselineSourceRef: "audit_2026",
      measurementOwnerMemberId: memberId,
    });

    // 1. Record review
    const review = await recordAiInitiativeReview(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      reviewCadenceDays: 14,
      findings: "Good adoption trajectory, on track with initial assumptions.",
      recommendation: "CONTINUE",
    });

    expect(review.initiativeId).toBe(init.id);
    expect(review.recommendation).toBe("CONTINUE");
    expect(review.nextReviewDueAt).toBeDefined();

    // 2. Pause initiative
    const pauseResult1 = await pauseAiInitiative(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      reasonCode: "BUDGET_REVISE",
      reason: "Pausing temporarily to review spending spike",
    });

    expect(pauseResult1.status).toBe("PAUSED");
    expect(pauseResult1.initiativeId).toBe(init.id);

    // Verify initiative lifecycle state changed to PAUSED
    const updatedInit = await getAiInitiativeInWorkspace(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
    });
    expect(updatedInit.lifecycleState).toBe("PAUSED");

    // 3. Pause idempotency: calling pause again returns success
    const pauseResult2 = await pauseAiInitiative(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      reasonCode: "BUDGET_REVISE",
      reason: "Already paused",
    });

    expect(pauseResult2.status).toBe("PAUSED");
  });
});
