import { describe, it, expect } from "vitest";
import { db } from "../models/db";
import { identityWorkspaces } from "../../shared/db/schema/identity";
import { stagePolicies, ventureStageTransitions } from "../../shared/db/schema/strategy";
import { eventOutbox } from "../../shared/db/schema/integration";
import { eq } from "drizzle-orm";
import { assessVentureStage, transitionVentureStage } from "../strategy/services/stage-lifecycle.service";
import { createTestWorkspaceWithMember } from "./_helpers";
import { generateSnowflake } from "../../shared/services/snowflake.service";

describe("venture stage lifecycle", () => {
  it("assess does not mutate workspace stage", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    const assess = await assessVentureStage(wsId);
    expect(assess.currentStage).toBe("S0_GENESIS");
    expect(assess.recommendedStage).toBe("S1_PROBLEM_VALIDATION");
    expect(assess.gatePassed).toBe(true);

    const [ws] = await db
      .select()
      .from(identityWorkspaces)
      .where(eq(identityWorkspaces.id, wsId));
    expect(ws.companyStage).toBe("S0_GENESIS");
  });

  it("S0 -> S1 succeeds when no gate policy configured; writes journal + outbox", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    const r = await transitionVentureStage({
      workspaceId: wsId,
      toStage: "S1_PROBLEM_VALIDATION",
      reason: "problem hypothesis + customer defined",
    });
    expect(r.toStage).toBe("S1_PROBLEM_VALIDATION");

    const [ws] = await db
      .select()
      .from(identityWorkspaces)
      .where(eq(identityWorkspaces.id, wsId));
    expect(ws.companyStage).toBe("S1_PROBLEM_VALIDATION");

    const jr = await db
      .select()
      .from(ventureStageTransitions)
      .where(eq(ventureStageTransitions.workspaceId, wsId));
    expect(jr.length).toBe(1);
    expect(jr[0].fromStage).toBe("S0_GENESIS");
    expect(jr[0].toStage).toBe("S1_PROBLEM_VALIDATION");

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
        toStage: "S2_SOLUTION_VALIDATION",
        reason: "trying to skip S1",
      })
    ).rejects.toThrow(/tối đa 1 bậc|invalid/i);
  });

  it("gate fail without override throws failedPrecondition; with override writes overrideFlag=true", async () => {
    const fixture = await createTestWorkspaceWithMember();
    const wsId = BigInt(fixture.workspaceId);

    // Seed a blocking stage policy for S1_PROBLEM_VALIDATION requiring minimumEvidenceScore = 10.0
    await db.insert(stagePolicies).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      stageKey: "S1_PROBLEM_VALIDATION",
      minimumEvidenceScore: 10.0,
      requirements: [{ key: "req1", description: "Must have high score", minCount: 5 }],
      blockingRiskRules: [],
    });

    await expect(
      transitionVentureStage({
        workspaceId: wsId,
        toStage: "S1_PROBLEM_VALIDATION",
        reason: "trying without evidence",
      })
    ).rejects.toMatchObject({ code: "failed_precondition" });

    const ok = await transitionVentureStage({
      workspaceId: wsId,
      toStage: "S1_PROBLEM_VALIDATION",
      reason: "founder override: thị trường khẩn",
      override: true,
    });
    expect(ok.overrideApplied).toBe(true);
    expect(ok.toStage).toBe("S1_PROBLEM_VALIDATION");

    const [ws] = await db
      .select()
      .from(identityWorkspaces)
      .where(eq(identityWorkspaces.id, wsId));
    expect(ws.companyStage).toBe("S1_PROBLEM_VALIDATION");

    const [jr] = await db
      .select()
      .from(ventureStageTransitions)
      .where(eq(ventureStageTransitions.workspaceId, wsId));
    expect(jr.overrideFlag).toBe(true);
  });
});
