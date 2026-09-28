import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember, seedObjectiveWithKeyResult } from "./_helpers";
import {
  createInitiativeService,
  createAiInitiativeInWorkspace,
  getInitiativeGateStatus,
} from "../services/initiative.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";

const { initiatives } = schema;

function makeTenantContext(wsId: string, userId: string): TenantContext {
  return {
    workspaceId: wsId,
    userId,
    membershipRole: "founder",
    permissions: ["*"],
    correlationId: "test-corr-ai-foundation",
  };
}

describe("AI Initiative Foundation & Project Scoping", () => {
  it("rejects create when projectId is absent instead of selecting a first row", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);

    await expect(
      createInitiativeService(
        {
          workspaceId: ws.workspaceId,
          title: "Missing project initiative",
          keyResultIds: [okr.keyResultId],
        },
        ws.bearerToken
      )
    ).rejects.toThrow("projectId is required");
  });

  it("rejects create when keyResultIds is absent instead of selecting a first row", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });

    await expect(
      createInitiativeService(
        {
          workspaceId: ws.workspaceId,
          projectId: ws.projectId,
          title: "Missing KR initiative",
        },
        ws.bearerToken
      )
    ).rejects.toThrow("keyResultId is required");
  });

  it("creates an AI initiative with full explicit project, KR, owner and tiers", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);
    const ctx = makeTenantContext(ws.workspaceId, ws.userId);

    const aiInit = await createAiInitiativeInWorkspace(ctx, {
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "AI Operating System Pilot",
      businessProblem: "Inefficient manual workflows",
      intendedOutcome: "Automate 50% repetitive queries",
      businessOwnerMemberId: ws.userId,
      keyResultIds: [okr.keyResultId],
      initiativeKind: "AI",
      riskTier: "MEDIUM",
      autonomyTier: "A1",
    });

    expect(aiInit.id).toBeDefined();
    expect(aiInit.initiativeKind).toBe("AI");
    expect(aiInit.lifecycleState).toBe("DISCOVER");
    expect(aiInit.riskTier).toBe("MEDIUM");
    expect(aiInit.autonomyTier).toBe("A1");
    expect(aiInit.legacyRemediationState).toBe("CLEAN");
  });

  it("marks preexisting incomplete rows NEEDS_REBIND and excludes them from promotion", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);
    const legacyId = generateSnowflake();

    // Insert legacy row marked NEEDS_REBIND
    await db.insert(initiatives).values({
      id: legacyId,
      workspaceId: BigInt(ws.workspaceId),
      projectId: BigInt(ws.projectId),
      keyResultId: BigInt(okr.keyResultId),
      title: "Legacy initiative needing rebind",
      status: "active",
      approvalStatus: "DRAFT",
      legacyRemediationState: "NEEDS_REBIND",
    });

    const gates = await getInitiativeGateStatus(legacyId.toString(), ws.workspaceId);
    expect(gates).toContainEqual("PROJECT_CONTEXT_REQUIRED");
  });
});
