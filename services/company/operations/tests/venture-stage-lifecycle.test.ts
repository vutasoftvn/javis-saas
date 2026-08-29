import { describe, it, expect } from "vitest";
import { db } from "../models/db";
import { identityWorkspaces } from "../../shared/db/schema/identity";
import { stagePolicies, workspaceStageTransitions } from "../../shared/db/schema/strategy";
import { eventOutbox } from "../../shared/db/schema/integration";
import { and, eq } from "drizzle-orm";
import { assessVentureStage, transitionVentureStage } from "../strategy/services/stage-lifecycle.service";
import { createTestWorkspaceWithMember } from "./_helpers";
import { generateSnowflake } from "../../shared/services/snowflake.service";

describe("venture stage lifecycle", () => {
  it("assess does not mutate workspace stage; missing policy ⇒ fail-closed", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    const assess = await assessVentureStage(wsId);
    expect(assess.currentStage).toBe("W0_IDEA");
    expect(assess.recommendedStage).toBe("W1_PROBLEM_VALIDATION");
    // M1 §7: không có policy ⇒ KHÔNG suy ra gatePassed=true.
    expect(assess.gatePassed).toBe(false);
    expect(assess.policyMissing).toBe(true);

    const [ws] = await db
      .select()
      .from(identityWorkspaces)
      .where(eq(identityWorkspaces.id, wsId));
    expect(ws.lifecycleStage).toBe("W0_IDEA");
  });

  it("M1 §7: missing policy blocks autonomous transitions", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    await expect(
      transitionVentureStage({
        workspaceId: wsId,
        toStage: "W1_PROBLEM_VALIDATION",
        reason: "agent thinks it's ready",
        actorRole: "founder",
        isAutonomous: true,
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });
  });

  it("M1 §7: missing policy — non-privileged human is denied", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    await expect(
      transitionVentureStage({
        workspaceId: wsId,
        toStage: "W1_PROBLEM_VALIDATION",
        reason: "regular member trying",
        actorRole: "member",
      })
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("M1 §7: missing policy — founder may proceed; writes journal + outbox", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    const r = await transitionVentureStage({
      workspaceId: wsId,
      toStage: "W1_PROBLEM_VALIDATION",
      reason: "founder: problem hypothesis + customer defined",
      actorRole: "founder",
    });
    expect(r.toStage).toBe("W1_PROBLEM_VALIDATION");

    const [ws] = await db
      .select()
      .from(identityWorkspaces)
      .where(eq(identityWorkspaces.id, wsId));
    expect(ws.lifecycleStage).toBe("W1_PROBLEM_VALIDATION");

    const jr = await db
      .select()
      .from(workspaceStageTransitions)
      .where(eq(workspaceStageTransitions.workspaceId, wsId));
    expect(jr.length).toBe(1);
    expect(jr[0].fromStage).toBe("W0_IDEA");
    expect(jr[0].toStage).toBe("W1_PROBLEM_VALIDATION");

    const ob = await db
      .select()
      .from(eventOutbox)
      .where(eq(eventOutbox.aggregateId, wsId.toString()));
    expect(ob.some((e) => e.eventType.startsWith("venture.stage.changed"))).toBe(true);
  });

  it("S0 -> S2 (skip) is rejected with invalidArgument", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    await expect(
      transitionVentureStage({
        workspaceId: wsId,
        toStage: "W2_SOLUTION_VALIDATION",
        reason: "trying to skip S1",
        actorRole: "founder",
      })
    ).rejects.toThrow(/tối đa 1 bậc|invalid/i);
  });

  it("M1 §7: gate fail — override requires founder/admin; agent cannot self-override", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    await db.insert(stagePolicies).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      stageKey: "W1_PROBLEM_VALIDATION",
      minimumEvidenceScore: 10.0,
      requirements: [{ key: "req1", description: "Must have high score", minCount: 5 }],
      blockingRiskRules: [],
    });

    // No override, gate fails ⇒ failedPrecondition.
    await expect(
      transitionVentureStage({
        workspaceId: wsId,
        toStage: "W1_PROBLEM_VALIDATION",
        reason: "no evidence",
        actorRole: "founder",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });

    // override by a regular member ⇒ permissionDenied.
    await expect(
      transitionVentureStage({
        workspaceId: wsId,
        toStage: "W1_PROBLEM_VALIDATION",
        reason: "member override attempt",
        actorRole: "member",
        override: true,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    // override by an autonomous agent ⇒ permissionDenied.
    await expect(
      transitionVentureStage({
        workspaceId: wsId,
        toStage: "W1_PROBLEM_VALIDATION",
        reason: "agent override attempt",
        actorRole: "founder",
        isAutonomous: true,
        override: true,
      })
    ).rejects.toMatchObject({ code: "permission_denied" });

    // founder override ⇒ succeeds, overrideFlag persisted, gate result not erased.
    const ok = await transitionVentureStage({
      workspaceId: wsId,
      toStage: "W1_PROBLEM_VALIDATION",
      reason: "founder override: thị trường khẩn",
      actorRole: "founder",
      override: true,
    });
    expect(ok.overrideApplied).toBe(true);

    const [jr] = await db
      .select()
      .from(workspaceStageTransitions)
      .where(eq(workspaceStageTransitions.workspaceId, wsId));
    expect(jr.overrideFlag).toBe(true);
    expect(jr.reason).toMatch(/override/i);
  });

  // ── M4 §2 ────────────────────────────────────────────────────────────────

  it("§2: same-stage request là no-op — không ghi history row, không bump version", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    const r = await transitionVentureStage({
      workspaceId: wsId,
      toStage: "W0_IDEA", // đang ở W0_IDEA
      reason: "noop",
      actorRole: "founder",
    });
    expect(r.noop).toBe(true);
    expect(r.stageVersion).toBe(0);

    const jr = await db
      .select()
      .from(workspaceStageTransitions)
      .where(eq(workspaceStageTransitions.workspaceId, wsId));
    expect(jr.length).toBe(0);
  });

  it("§2: transition bump stage_version + ghi provenance (source, stageVersionFrom, evidence snapshot)", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    const r = await transitionVentureStage({
      workspaceId: wsId,
      toStage: "W1_PROBLEM_VALIDATION",
      reason: "founder: ready",
      actorRole: "founder",
      source: "manual",
    });
    expect(r.noop).toBe(false);
    expect(r.stageVersion).toBe(1);

    const [ws] = await db
      .select()
      .from(identityWorkspaces)
      .where(eq(identityWorkspaces.id, wsId));
    expect(ws.stageVersion).toBe(1);

    const [jr] = await db
      .select()
      .from(workspaceStageTransitions)
      .where(eq(workspaceStageTransitions.workspaceId, wsId));
    expect(jr.stageVersionFrom).toBe(0);
    expect(jr.source).toBe("manual");
    expect(jr.actorRole).toBe("founder");
    expect((jr.evidenceSnapshot as Record<string, unknown>).evidenceCount).toBe(0);
    expect((jr.evaluationResult as Record<string, unknown>).policyMissing).toBe(true);
  });

  it("§2: CAS predicate — UPDATE với stage_version cũ khớp 0 row (nền tảng chống double-transition)", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    // Transition thật ⇒ stage_version 0 -> 1.
    await transitionVentureStage({
      workspaceId: wsId,
      toStage: "W1_PROBLEM_VALIDATION",
      reason: "bump",
      actorRole: "founder",
    });

    // Một "transition đồng thời" xuất phát từ stage_version=0 (đã cũ) ⇒ WHERE khớp 0 row,
    // đúng cơ chế service dùng để từ chối cái thua bằng APIError.aborted.
    const stale = await db
      .update(identityWorkspaces)
      .set({ lifecycleStage: "W2_SOLUTION_VALIDATION", stageVersion: 1 })
      .where(and(eq(identityWorkspaces.id, wsId), eq(identityWorkspaces.stageVersion, 0)))
      .returning({ id: identityWorkspaces.id });
    expect(stale.length).toBe(0);

    // Transition kế tiếp (đọc version hiện tại = 1) vẫn chạy bình thường ⇒ version 2.
    const r = await transitionVentureStage({
      workspaceId: wsId,
      toStage: "W2_SOLUTION_VALIDATION",
      reason: "next",
      actorRole: "founder",
    });
    expect(r.stageVersion).toBe(2);
  });
});
