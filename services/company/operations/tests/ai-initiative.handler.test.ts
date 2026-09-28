import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createTestWorkspaceWithMember, seedObjectiveWithKeyResult } from "./_helpers";
import {
  createAiInitiative,
  getAiInitiative,
  transitionAiInitiative,
} from "../handlers/ai-initiative.handler";

const { initiatives } = schema;

describe("AI Initiative Handler", () => {
  it("creates and retrieves an AI initiative through the HTTP contract", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);

    const created = await createAiInitiative({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "Contract Tested AI Initiative",
      businessProblem: "Manual ticket triaging is slow and inconsistent",
      intendedOutcome: "Triage 90% of incoming tickets in under 5 minutes",
      businessOwnerMemberId: ws.userId,
      keyResultIds: [okr.keyResultId],
      riskTier: "MEDIUM",
      autonomyTier: "A1",
    });

    expect(created.id).toBeDefined();
    expect(created.projectId).toBe(ws.projectId);
    expect(created.lifecycleState).toBe("DISCOVER");
    expect(created.approvalStatus).toBe("DRAFT");
    expect(created.riskTier).toBe("MEDIUM");
    expect(created.autonomyTier).toBe("A1");

    const fetched = await getAiInitiative({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: created.id,
    });

    expect(fetched.id).toBe(created.id);
    expect(fetched.title).toBe(created.title);
    expect(fetched.projectId).toBe(ws.projectId);
  });

  it("enforces mandatory params on transition endpoint", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);

    const init = await createAiInitiative({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "Transition Validation Initiative",
      businessProblem: "Customer response lag",
      intendedOutcome: "Automated routing",
      businessOwnerMemberId: ws.userId,
      keyResultIds: [okr.keyResultId],
    });

    // Missing expectedRevision
    await expect(
      transitionAiInitiative({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        projectId: ws.projectId,
        initiativeId: init.id,
        targetState: "PILOT",
        expectedRevision: undefined as any,
        reasonCode: "START_PILOT",
      })
    ).rejects.toThrow("expectedRevision is required");

    // Missing reasonCode
    await expect(
      transitionAiInitiative({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        projectId: ws.projectId,
        initiativeId: init.id,
        targetState: "PILOT",
        expectedRevision: init.revision,
        reasonCode: "   ",
      })
    ).rejects.toThrow("reasonCode is required");
  });

  it("transitions initiative once approved and records the decision", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const okr = await seedObjectiveWithKeyResult(ws.workspaceId, ws.projectId);

    const init = await createAiInitiative({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      title: "Approved AI Initiative",
      businessProblem: "Manual reconciliation",
      intendedOutcome: "Automated ledger balancing",
      businessOwnerMemberId: ws.userId,
      keyResultIds: [okr.keyResultId],
    });

    // Mark as approved
    await db
      .update(initiatives)
      .set({ approvalStatus: "APPROVED" })
      .where(eq(initiatives.id, BigInt(init.id)));

    const result = await transitionAiInitiative({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: ws.projectId,
      initiativeId: init.id,
      targetState: "PILOT",
      expectedRevision: init.revision,
      reasonCode: "PILOT_KICKOFF",
      reason: "Discovery completed and approved by stakeholder",
    });

    expect(result.currentState).toBe("PILOT");
    expect(result.lifecycleState).toBe("PILOT");
    expect(result.decision.id).toBeDefined();
    expect(result.decision.reasonCode).toBe("PILOT_KICKOFF");
    expect(result.initiative.revision).toBe(init.revision + 1);
  });
});
