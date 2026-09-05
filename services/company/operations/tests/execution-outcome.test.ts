import { describe, it, expect } from "vitest";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import {
  computeLinearProgress,
  calculateExecutionScore,
  calculateOutcomeScore,
  validateTaskCompletion,
} from "../services/execution-outcome.service";
import { recordKrObservation } from "../services/kr-observation.service";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const {
  okrCycles,
  okrObjectives,
  keyResults,
  krObservations,
  cycleKeyResults,
  twelveWeekCycles,
  tasks,
} = schema;

describe("Linear Progress Calculation (Pure Logic)", () => {
  it("computes decreasing progress correctly", () => {
    expect(computeLinearProgress({ baseline: 10, target: 5, current: 8 })).toBeCloseTo(0.4);
    expect(computeLinearProgress({ baseline: 10, target: 5, current: 5 })).toBe(1.0);
    expect(computeLinearProgress({ baseline: 10, target: 5, current: 12 })).toBe(0.0);
  });

  it("computes increasing progress correctly", () => {
    expect(computeLinearProgress({ baseline: 100, target: 200, current: 150 })).toBeCloseTo(0.5);
    expect(computeLinearProgress({ baseline: 100, target: 200, current: 200 })).toBe(1.0);
    expect(computeLinearProgress({ baseline: 100, target: 200, current: 250 })).toBe(1.0); // clamped
    expect(computeLinearProgress({ baseline: 100, target: 200, current: 50 })).toBe(0.0); // clamped
  });

  it("returns null when target equals baseline or data is missing", () => {
    expect(computeLinearProgress({ baseline: 5, target: 5, current: 5 })).toBeNull();
    expect(computeLinearProgress({ baseline: null, target: 10, current: 5 })).toBeNull();
    expect(computeLinearProgress({ baseline: 10, target: null, current: 5 })).toBeNull();
    expect(computeLinearProgress({ baseline: 10, target: 20, current: null })).toBeNull();
    expect(computeLinearProgress({ baseline: NaN, target: 20, current: 15 })).toBeNull();
  });
});

describe("Execution & Outcome Scores (Pure Logic)", () => {
  it("calculates execution score based on completed commitments with evidence", () => {
    // 0 commitments -> null
    expect(calculateExecutionScore([])).toBeNull();

    // 2 done with evidence out of 3 -> 2/3
    const score = calculateExecutionScore([
      { status: "done", hasEligibleEvidence: true },
      { status: "done", hasEligibleEvidence: true },
      { status: "todo", hasEligibleEvidence: false },
    ]);
    expect(score).toBeCloseTo(0.6667, 3);

    // Done task without eligible evidence is excluded from numerator
    const scoreWithoutEvidence = calculateExecutionScore([
      { status: "done", hasEligibleEvidence: false },
      { status: "done", hasEligibleEvidence: true },
    ]);
    expect(scoreWithoutEvidence).toBe(0.5);
  });

  it("calculates outcome score based on valid KR progress", () => {
    expect(calculateOutcomeScore([])).toBeNull();
    expect(calculateOutcomeScore([{ score: null }])).toBeNull();

    const outcome = calculateOutcomeScore([
      { score: 0.4 },
      { score: 0.8 },
      { score: null },
    ]);
    expect(outcome).toBeCloseTo(0.6);
  });
});

describe("Key Result Observations & Task Completion (DB Operations)", () => {
  async function seedOkrFixture() {
    const ws = await createTestWorkspaceWithMember();
    const wsId = BigInt(ws.workspaceId);

    // 1. Create OKR Cycle
    const [cycle] = await db
      .insert(okrCycles)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        name: "Q3 Strategy Cycle",
        status: "active",
      })
      .returning();

    // 2. Create Objective
    const [obj] = await db
      .insert(okrObjectives)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        cycleId: cycle!.id,
        title: "Achieve Product-Market Fit",
      })
      .returning();

    // 3. Create Key Result
    const [kr] = await db
      .insert(keyResults)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        objectiveId: obj!.id,
        title: "Customer acquisition cost under $50",
        baselineValue: 100,
        currentValue: 100,
        targetValue: 50,
        scoringType: "LINEAR_DECREASE",
      })
      .returning();

    return {
      workspaceId: ws.workspaceId,
      auth: ws.bearerToken,
      krId: kr!.id.toString(),
      cycleId: cycle!.id.toString(),
    };
  }

  it("records KR observation and updates currentValue", async () => {
    const { workspaceId, krId } = await seedOkrFixture();
    const obs = await recordKrObservation(
      {
        workspaceId,
        userId: "1",
        membershipRole: "founder",
        permissions: [],
        correlationId: "obs-1",
      },
      {
        krId,
        value: 75,
        measurementAt: "2026-09-07T10:00:00Z",
      }
    );

    expect(obs.valueDecimal).toBe("75.0000");
    // Progress: (100 - 75) / (100 - 50) = 25 / 50 = 0.5
    expect(obs.projectedProgress).toBeCloseTo(0.5);

    const [updatedKr] = await db
      .select()
      .from(keyResults)
      .where(eq(keyResults.id, BigInt(krId)));
    expect(updatedKr!.currentValue).toBe(75);
  });

  it("does not roll back currentValue on late-arriving observation", async () => {
    const { workspaceId, krId } = await seedOkrFixture();
    const ctx = {
      workspaceId,
      userId: "1",
      membershipRole: "founder",
      permissions: [],
      correlationId: "obs-seq",
    };

    // New observation at T2 (value = 60)
    await recordKrObservation(ctx, {
      krId,
      value: 60,
      measurementAt: "2026-09-08T12:00:00Z",
    });

    const [krAfterT2] = await db
      .select()
      .from(keyResults)
      .where(eq(keyResults.id, BigInt(krId)));
    expect(krAfterT2!.currentValue).toBe(60);

    // Late observation arrived later with measurementAt T1 (value = 80)
    await recordKrObservation(ctx, {
      krId,
      value: 80,
      measurementAt: "2026-09-07T12:00:00Z", // older!
    });

    // Current value must remain 60 (late observation does NOT roll back)
    const [krAfterLate] = await db
      .select()
      .from(keyResults)
      .where(eq(keyResults.id, BigInt(krId)));
    expect(krAfterLate!.currentValue).toBe(60);

    // Both observations are safely recorded append-only
    const rows = await db
      .select()
      .from(krObservations)
      .where(eq(krObservations.krId, BigInt(krId)));
    expect(rows.length).toBe(2);
  });

  it("handles idempotent observation submission without duplication", async () => {
    const { workspaceId, krId } = await seedOkrFixture();
    const ctx = {
      workspaceId,
      userId: "1",
      membershipRole: "founder",
      permissions: [],
      correlationId: "idem-obs",
    };

    const first = await recordKrObservation(ctx, {
      krId,
      value: 70,
      idempotencyKey: "unique-batch-key-999",
    });

    const duplicate = await recordKrObservation(ctx, {
      krId,
      value: 70,
      idempotencyKey: "unique-batch-key-999",
    });

    expect(duplicate.id).toBe(first.id);

    const rows = await db
      .select()
      .from(krObservations)
      .where(eq(krObservations.krId, BigInt(krId)));
    expect(rows.length).toBe(1);
  });

  it("links single KR across multiple cycles without observation pollution", async () => {
    const { workspaceId, krId, auth } = await seedOkrFixture();
    const wsId = BigInt(workspaceId);

    // Create 2 TwelveWeekCycles
    const [c1] = await db
      .insert(twelveWeekCycles)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        displayName: "Cycle 1",
        durationWeeks: 6,
      })
      .returning();

    const [c2] = await db
      .insert(twelveWeekCycles)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        displayName: "Cycle 2",
        durationWeeks: 6,
      })
      .returning();

    // Link same KR to both cycles
    await db.insert(cycleKeyResults).values([
      { workspaceId: wsId, cycleId: c1!.id, keyResultId: BigInt(krId) },
      { workspaceId: wsId, cycleId: c2!.id, keyResultId: BigInt(krId) },
    ]);

    const links = await db
      .select()
      .from(cycleKeyResults)
      .where(eq(cycleKeyResults.keyResultId, BigInt(krId)));
    expect(links.length).toBe(2);
  });

  it("completing a task does NOT automatically increment KR progress", async () => {
    const { workspaceId, krId } = await seedOkrFixture();
    const wsId = BigInt(workspaceId);

    // Create a task
    const taskId = generateSnowflake();
    await db.insert(tasks).values({
      id: taskId,
      workspaceId: wsId,
      title: "Chạy chiến dịch quảng cáo",
      status: "todo",
      revision: 1,
    });

    // Complete the task
    const res = await validateTaskCompletion(
      {
        workspaceId,
        userId: "1",
        membershipRole: "founder",
        permissions: [],
        correlationId: "task-done-1",
      },
      {
        taskId: taskId.toString(),
        expectedVersion: 1,
        evidenceRefs: ["ev_ad_receipt"],
      }
    );

    expect(res.status).toBe("done");
    expect(res.revision).toBe(2);

    // Check that KR currentValue was NOT automatically modified
    const [kr] = await db
      .select()
      .from(keyResults)
      .where(eq(keyResults.id, BigInt(krId)));
    expect(kr!.currentValue).toBe(100); // untouched!
  });
});
