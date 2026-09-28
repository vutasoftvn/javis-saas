import { describe, it, expect } from "vitest";
import { sql, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestWorkspaceWithMember, seedObjectiveWithKeyResult } from "./_helpers";
import { createAiInitiativeInWorkspace } from "../services/initiative.service";
import {
  recordValueContract,
  recordDataReadinessAssessment,
  setBudgetPolicy,
} from "../services/ai-initiative-evidence.service";
import { transitionAiInitiative } from "../services/ai-initiative-transition.service";
import {
  publishPromotionSnapshotToCosa,
  setCustomPromotionPublisher,
  computeDecisionHash,
  AiInitiativePromotionSnapshot,
} from "../services/ai-initiative-cosa.client";
import { outboxFor } from "../../shared/events/outbox.repository";
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
    correlationId: "test-corr-cosa-client",
  };
}

describe("AI Initiative COSA Client & Outbox Integration", () => {
  it("persists the outbox event before publishing a SCALE_CANDIDATE decision", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);
    const memberId = await seedHumanMember(ws.workspaceId, ws.userId);
    const ctx = makeTenantContext(ws.workspaceId, ws.userId, memberId);

    const init = await createAiInitiativeInWorkspace(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "Scale Candidate Initiative",
      businessProblem: "Manual reconciliation bottlenecks",
      intendedOutcome: "Automated ledger reconciliation with audit compliance",
      businessOwnerMemberId: ws.userId,
      keyResultIds: [okr.keyResultId],
    });

    // Mark as approved and move to PILOT
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
        reasonCode: "PILOT_START",
      },
      ctx
    );

    // Attach required evidence for VALIDATE and SCALE_CANDIDATE
    await recordValueContract(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      metricContractId: "reconciliation-time",
      baselineValue: "120.0",
      targetValue: "15.0",
      baselineSourceRef: "audit-report-q1.pdf",
      measurementOwnerMemberId: memberId,
    });

    await recordDataReadinessAssessment(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      assessmentStatus: "READY",
      classification: "INTERNAL",
      metadataOwnerMemberId: memberId,
    });

    const valResult = await transitionAiInitiative(
      {
        workspaceId: ws.workspaceId,
        projectId: ws.projectId,
        initiativeId: init.id,
        targetState: "VALIDATE",
        expectedRevision: pilotResult.initiative.revision,
        reasonCode: "VALIDATE_START",
      },
      ctx
    );

    // Set budget policy required for SCALE_CANDIDATE
    await setBudgetPolicy(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      softCostThreshold: "100.00",
      hardCostThreshold: "500.00",
      period: "MONTHLY",
    });

    const scaleCandidateResult = await transitionAiInitiative(
      {
        workspaceId: ws.workspaceId,
        projectId: ws.projectId,
        initiativeId: init.id,
        targetState: "SCALE_CANDIDATE",
        expectedRevision: valResult.initiative.revision,
        reasonCode: "SCALE_READY",
      },
      ctx
    );

    expect(scaleCandidateResult.currentState).toBe("SCALE_CANDIDATE");

    // Verify outbox persistence
    const outboxRow = await outboxFor(scaleCandidateResult.decision.id);
    expect(outboxRow).not.toBeNull();
    expect(outboxRow).toMatchObject({
      eventType: "ai.initiative.promoted.v1",
      aggregateType: "ai_initiative",
      aggregateId: init.id,
    });

    const payload = outboxRow!.envelope.payload;
    expect(payload.initiative_id).toBe(init.id);
    expect(payload.to_state).toBe("SCALE_CANDIDATE");
    expect(payload.snapshot).toBeDefined();
    expect(payload.snapshot.decisionHash).toBeDefined();
    expect(payload.snapshot.decisionId).toBe(scaleCandidateResult.decision.id);
  });

  it("publishes snapshot to COSA and handles retry idempotently", async () => {
    let callCount = 0;
    setCustomPromotionPublisher(async (snapshot) => {
      callCount++;
      return {
        accepted: true,
        status: callCount > 1 ? "already_consumed" : "accepted",
        decisionId: snapshot.decisionId,
      };
    });

    try {
      const snapshot: AiInitiativePromotionSnapshot = {
        initiativeId: "init-100",
        initiativeRevision: 2,
        workspaceId: "ws-1",
        projectId: "proj-1",
        lifecycleState: "PILOT",
        riskTier: "LOW",
        autonomyTier: "A0",
        decisionId: "dec-100",
        decisionHash: computeDecisionHash("dec-100", 2, "PILOT", "ws-1", "proj-1"),
        pins: {},
      };

      const res1 = await publishPromotionSnapshotToCosa(snapshot);
      expect(res1.accepted).toBe(true);
      expect(res1.status).toBe("accepted");

      // Second call: idempotent
      const res2 = await publishPromotionSnapshotToCosa(snapshot);
      expect(res2.accepted).toBe(true);
      expect(res2.status).toBe("already_consumed");
    } finally {
      setCustomPromotionPublisher(null);
    }
  });

  it("rejects when COSA returns 403 on foreign project or hash drift", async () => {
    setCustomPromotionPublisher(async (snapshot) => {
      if (snapshot.projectId.includes("foreign") || snapshot.decisionHash.includes("drift")) {
        const { APIError } = await import("encore.dev/api");
        throw APIError.permissionDenied("COSA rejected snapshot: foreign project or hash drift");
      }
      return { accepted: true, status: "accepted", decisionId: snapshot.decisionId };
    });

    try {
      const foreignSnapshot: AiInitiativePromotionSnapshot = {
        initiativeId: "init-200",
        initiativeRevision: 1,
        workspaceId: "ws-1",
        projectId: "foreign_project",
        lifecycleState: "PILOT",
        riskTier: "LOW",
        autonomyTier: "A0",
        decisionId: "dec-200",
        decisionHash: "valid-hash-123456",
        pins: {},
      };

      await expect(
        publishPromotionSnapshotToCosa(foreignSnapshot)
      ).rejects.toThrow("COSA rejected snapshot: foreign project or hash drift");
    } finally {
      setCustomPromotionPublisher(null);
    }
  });
});
