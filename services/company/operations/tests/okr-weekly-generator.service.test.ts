// services/company/operations/tests/okr-weekly-generator.service.test.ts
//
// TDD cho generateCycleFromObjective (Task 5): sinh Operating Cycle + N
// weekly_plans rỗng từ 1 Objective OKR đã publish.
import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createObjective, addKeyResult, publishObjective } from "../handlers/okr.handler";
import { generateCycleFromObjective } from "../services/okr-weekly-generator.service";
import { db, schema } from "../models/db";
import type { TenantContext } from "../../shared/types/tenant_context";

function ctxFor(workspaceId: string, userId: string): TenantContext {
  return Object.freeze({
    workspaceId,
    userId,
    workforceMemberId: userId,
    membershipRole: "founder",
    permissions: [],
    correlationId: "test-okr-weekly-generator",
    platformUserId: null,
  }) as unknown as TenantContext;
}

/**
 * Tạo một objective đã publish (đủ 1 Key Result hợp lệ theo yêu cầu
 * publishObjectiveService) để dùng làm nguồn cho generator.
 */
async function makePublishedObjective() {
  const session = await createTestSession({ displayName: "OKR Weekly Gen", role: "founder" });
  const authorization = `Bearer ${session.accessToken}`;

  const objective = await createObjective({
    workspaceId: session.workspaceId,
    title: "Grow MRR",
    authorization,
  });

  await addKeyResult({
    objectiveId: objective.id,
    title: "MRR to $50k",
    targetValue: 50000,
    baselineValue: 10000,
    unit: "USD",
    authorization,
  });

  await publishObjective({
    id: objective.id,
    workspaceId: session.workspaceId,
    authorization,
  });

  return { session, objective };
}

describe("generateCycleFromObjective", () => {
  it("creates a cycle with the requested duration and one empty weekly_plan per week", async () => {
    const { session, objective } = await makePublishedObjective();
    const ctx = ctxFor(session.workspaceId, session.userId);

    const cycle = await generateCycleFromObjective(ctx, objective.id, 4);

    expect(cycle.durationWeeks).toBe(4);
    expect(cycle.sourceObjectiveId).toBe(objective.id);

    const plans = await db
      .select()
      .from(schema.weeklyPlans)
      .where(eq(schema.weeklyPlans.cycleId, BigInt(cycle.id)));
    expect(plans).toHaveLength(4);
    expect(plans.map((p) => p.weekNo).sort()).toEqual([1, 2, 3, 4]);
  });

  it("rejects when objective is not published", async () => {
    const session = await createTestSession({ displayName: "OKR Weekly Gen Draft", role: "founder" });
    const authorization = `Bearer ${session.accessToken}`;
    const objective = await createObjective({
      workspaceId: session.workspaceId,
      title: "Draft objective",
      authorization,
    });
    const ctx = ctxFor(session.workspaceId, session.userId);

    await expect(generateCycleFromObjective(ctx, objective.id, 4)).rejects.toThrow();
  });
});
