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
  weeklyPlans,
  weeklyCommitments,
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

  it("rejects a garbage-suffixed numeric string instead of silently truncating it (IA27)", async () => {
    const { workspaceId, krId } = await seedOkrFixture();
    const ctx = {
      workspaceId,
      userId: "1",
      membershipRole: "founder",
      permissions: [],
      correlationId: "obs-garbage",
    };

    // parseFloat("12junk") === 12 — trước đây được chấp nhận âm thầm.
    await expect(
      recordKrObservation(ctx, {
        krId,
        value: "12junk",
        measurementAt: "2026-09-07T10:00:00Z",
      })
    ).rejects.toThrow(/Invalid numeric observation value/);

    // KR không bị đổi bởi observation rác đã bị từ chối.
    const [kr] = await db.select().from(keyResults).where(eq(keyResults.id, BigInt(krId)));
    expect(kr!.currentValue).toBe(100);
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

  it("rejects completing a task with no evidence instead of silently marking it DONE (IA22/IA23)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const wsId = BigInt(ws.workspaceId);
    const ctx = {
      workspaceId: ws.workspaceId,
      userId: "1",
      membershipRole: "founder",
      permissions: [],
      correlationId: "no-evidence-test",
    };

    const taskId = generateSnowflake();
    await db.insert(tasks).values({
      id: taskId,
      workspaceId: wsId,
      title: "Task without evidence",
      status: "todo",
      revision: 1,
    });

    // Trước fix: evidenceRefs chỉ được forward vào event payload, không hề
    // được kiểm tra — task DONE mà không có bằng chứng nào vẫn đóng góp
    // điểm execution score như thể đã hoàn thành thật.
    await expect(
      validateTaskCompletion(ctx, { taskId: taskId.toString(), expectedVersion: 1 })
    ).rejects.toThrow(/evidence/i);
    await expect(
      validateTaskCompletion(ctx, { taskId: taskId.toString(), expectedVersion: 1, evidenceRefs: ["   "] })
    ).rejects.toThrow(/evidence/i);

    const [stillTodo] = await db.select().from(tasks).where(eq(tasks.id, taskId));
    expect(stillTodo!.status).toBe("todo");
    expect(stillTodo!.revision).toBe(1);
  });

  it("does not close the parent commitment while a sibling task is still pending (IA23)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const wsId = BigInt(ws.workspaceId);
    const ctx = {
      workspaceId: ws.workspaceId,
      userId: "1",
      membershipRole: "founder",
      permissions: [],
      correlationId: "sibling-test",
    };

    const [cycle] = await db
      .insert(twelveWeekCycles)
      .values({ id: generateSnowflake(), workspaceId: wsId, durationWeeks: 6 })
      .returning();
    const [plan] = await db
      .insert(weeklyPlans)
      .values({ id: generateSnowflake(), workspaceId: wsId, cycleId: cycle!.id, weekNo: 1 })
      .returning();
    const [commitment] = await db
      .insert(weeklyCommitments)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        weeklyPlanId: plan!.id,
        title: "Ship onboarding flow",
      })
      .returning();

    const taskAId = generateSnowflake();
    const taskBId = generateSnowflake();
    await db.insert(tasks).values([
      {
        id: taskAId,
        workspaceId: wsId,
        title: "Task A",
        status: "todo",
        revision: 1,
        weeklyCommitmentId: commitment!.id,
      },
      {
        id: taskBId,
        workspaceId: wsId,
        title: "Task B (still pending)",
        status: "todo",
        revision: 1,
        weeklyCommitmentId: commitment!.id,
      },
    ]);

    // Complete task A only — task B (sibling) is still "todo".
    await validateTaskCompletion(ctx, {
      taskId: taskAId.toString(),
      expectedVersion: 1,
      evidenceRefs: ["ev_a"],
    });

    const [commitmentAfterA] = await db
      .select()
      .from(weeklyCommitments)
      .where(eq(weeklyCommitments.id, commitment!.id));
    expect(commitmentAfterA!.status).not.toBe("done");

    // Complete task B — now both siblings are done, commitment should close.
    await validateTaskCompletion(ctx, {
      taskId: taskBId.toString(),
      expectedVersion: 1,
      evidenceRefs: ["ev_b"],
    });

    const [commitmentAfterB] = await db
      .select()
      .from(weeklyCommitments)
      .where(eq(weeklyCommitments.id, commitment!.id));
    expect(commitmentAfterB!.status).toBe("done");
  });

  it("two concurrent completions of the same task never both report success with the same revision (IA23)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const wsId = BigInt(ws.workspaceId);
    const ctx = {
      workspaceId: ws.workspaceId,
      userId: "1",
      membershipRole: "founder",
      permissions: [],
      correlationId: "cas-race-test",
    };

    const taskId = generateSnowflake();
    await db.insert(tasks).values({
      id: taskId,
      workspaceId: wsId,
      title: "Racy task",
      status: "todo",
      revision: 1,
    });

    const results = await Promise.allSettled([
      validateTaskCompletion(ctx, { taskId: taskId.toString(), evidenceRefs: ["ev_x"] }),
      validateTaskCompletion(ctx, { taskId: taskId.toString(), evidenceRefs: ["ev_y"] }),
    ]);

    // Cả 2 phải hội tụ đúng: hoặc 1 thắng ghi revision=2 và bên kia thấy
    // status="done" đã tồn tại (idempotent no-op), hoặc DB CAS chặn 1 bên —
    // KHÔNG được có chuyện cả 2 cùng "thành công" nhưng task chỉ tăng
    // revision đúng 1 lần (mất 1 update).
    const fulfilled = results.filter((r) => r.status === "fulfilled") as PromiseFulfilledResult<any>[];
    expect(fulfilled.length).toBeGreaterThanOrEqual(1);

    const [finalTask] = await db.select().from(tasks).where(eq(tasks.id, taskId));
    expect(finalTask!.status).toBe("done");
    expect(finalTask!.revision).toBe(2);

    // Mọi kết quả fulfilled phải phản ánh đúng trạng thái cuối (revision=2),
    // không có kết quả "done, revision=2" bị báo trùng từ 2 lần tăng riêng biệt.
    for (const r of fulfilled) {
      expect(r.value.revision).toBe(2);
    }
  });
});
