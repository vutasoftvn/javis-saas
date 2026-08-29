import { describe, it, expect } from "vitest";
import { db } from "../../identity/models/db";
import { identityWorkspaces } from "../../shared/db/schema/identity";
import { workspaceStageTransitions } from "../../shared/db/schema/strategy";
import { eventOutbox } from "../../shared/db/schema/integration";
import { eq } from "drizzle-orm";
import { getWorkspaceRecord } from "../../identity/services/workspace.service";
import {
  assessVentureStage,
  transitionVentureStage,
} from "../../operations/strategy/services/stage-lifecycle.service";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

describe("Release A: End-to-End Provisioning, Stage Lifecycle & Tenant Isolation", () => {
  it("Step 1: Workspace has lifecycleStage=W0_IDEA", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const ws = await getWorkspaceRecord(fixture.workspaceId);

    expect(ws.lifecycleStage).toBe("W0_IDEA");
    expect(ws.lifecycleStage).toBe("W0_IDEA");
    expect(ws.stageEnteredAt).toBeNull();
  });

  it("Step 2: assess does not change stage", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    const assess = await assessVentureStage(wsId);
    expect(assess.currentStage).toBe("W0_IDEA");
    expect(assess.recommendedStage).toBe("W1_PROBLEM_VALIDATION");
    // M1 §7: no stage policy ⇒ fail-closed, không suy ra gatePassed=true.
    expect(assess.gatePassed).toBe(false);
    expect(assess.policyMissing).toBe(true);

    const ws = await getWorkspaceRecord(fixture.workspaceId);
    expect(ws.lifecycleStage).toBe("W0_IDEA");
  });

  it("Step 3: transition S0 -> S1 passes, writes journal row and outbox event", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    const result = await transitionVentureStage({
      workspaceId: wsId,
      toStage: "W1_PROBLEM_VALIDATION",
      reason: "Initial problem hypothesis validated with 5 customer interviews",
      actorMemberId: BigInt(fixture.userId),
      actorRole: "admin", // createTestWorkspaceWithMember default role
    });

    expect(result.fromStage).toBe("W0_IDEA");
    expect(result.toStage).toBe("W1_PROBLEM_VALIDATION");

    const ws = await getWorkspaceRecord(fixture.workspaceId);
    expect(ws.lifecycleStage).toBe("W1_PROBLEM_VALIDATION");
    expect(ws.stageEnteredAt).not.toBeNull();

    // Verify journal row
    const transitions = await db
      .select()
      .from(workspaceStageTransitions)
      .where(eq(workspaceStageTransitions.workspaceId, wsId));
    expect(transitions.length).toBe(1);
    expect(transitions[0].fromStage).toBe("W0_IDEA");
    expect(transitions[0].toStage).toBe("W1_PROBLEM_VALIDATION");

    // Verify outbox event
    const events = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, wsId.toString()));
    expect(events.some((e) => e.eventType.startsWith("venture.stage.changed"))).toBe(true);
  });

  it("Step 4: transition S1 -> S3 (skipping S2) is strictly rejected", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    await expect(
      transitionVentureStage({
        workspaceId: wsId,
        toStage: "W3_MVP_BUILD",
        reason: "trying to skip solution validation",
      })
    ).rejects.toThrow(/tối đa 1 bậc|invalid/i);
  });

  it("Step 5: Tenant isolation - User B cannot access Workspace A", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember();

    // User B tries to access Workspace A
    await expect(
      requireWorkspaceAccess(wsB.bearerToken, wsA.workspaceId)
    ).rejects.toMatchObject({ code: "permission_denied" });

    // User A can access Workspace A
    const ctxA = await requireWorkspaceAccess(wsA.bearerToken, wsA.workspaceId);
    expect(ctxA.workspaceId).toBe(wsA.workspaceId);
  });
});
