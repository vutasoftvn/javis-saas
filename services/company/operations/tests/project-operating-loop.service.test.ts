import { describe, it, expect, beforeEach } from "vitest";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createTestWorkspaceWithMember } from "./_helpers";
import type { TenantContext } from "../../shared/types/tenant_context";
import { createProjectService } from "../services/project.service";
import {
  createObjectiveAuthorized,
  createKeyResultAuthorized,
  createInitiativeAuthorized,
  createCycleAuthorized,
  createWeeklyPlanAuthorized,
  createWeeklyCommitmentAuthorized,
  createTaskAuthorized,
  advanceTaskService,
  advanceCycleWeekAuthorized,
  getProjectOperatingLoop,
} from "../services/project-operating-loop.service";

function ctxFor(workspaceId: string, userId = "1"): TenantContext {
  return Object.freeze({
    workspaceId,
    userId,
    workforceMemberId: undefined,
    membershipRole: "admin",
    permissions: [],
    correlationId: "test-operating-loop",
    platformUserId: null,
  }) as unknown as TenantContext;
}

describe("project-operating-loop service hierarchy & tenant enforcement", () => {
  it("rejects cross-project and cross-workspace hierarchy links and guards task progression", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember();
    const ctxA = ctxFor(wsA.workspaceId, wsA.userId);
    const ctxB = ctxFor(wsB.workspaceId, wsB.userId);

    const projectA = await createProjectService(ctxA, { title: "Project A" });
    const projectB = await createProjectService(ctxB, { title: "Project B" });

    // 1. Create Objective and Key Result in Project B
    const objectiveB = await createObjectiveAuthorized(ctxB, {
      projectId: projectB.id,
      title: "Objective B",
    });

    const keyResultB = await createKeyResultAuthorized(ctxB, {
      projectId: projectB.id,
      objectiveId: objectiveB.id,
      title: "KR B",
    });

    // 2. Reject Initiative in Project A pointing to Key Result from Project B
    await expect(
      createInitiativeAuthorized(ctxA, {
        projectId: projectA.id,
        keyResultId: keyResultB.id,
        title: "Must reject cross-project KR",
      })
    ).rejects.toThrow(/project|workspace/i);

    // 3. Reject Cycle with duration outside 1..12
    await expect(
      createCycleAuthorized(ctxA, {
        projectId: projectA.id,
        durationWeeks: 13,
      })
    ).rejects.toThrow(/duration_weeks|duration/i);

    // 4. Create Cycle in Project A (duration 12)
    const cycleA = await createCycleAuthorized(ctxA, {
      projectId: projectA.id,
      durationWeeks: 12,
      theme: "Q1 Execution",
    });
    expect(cycleA.projectId).toBe(projectA.id);

    // 5. Reject a second ACTIVE cycle on the same project
    await expect(
      createCycleAuthorized(ctxA, {
        projectId: projectA.id,
        durationWeeks: 6,
      })
    ).rejects.toThrow(/active/i);

    // 6. Create Weekly Plan in Project A
    const week1 = await createWeeklyPlanAuthorized(ctxA, {
      projectId: projectA.id,
      cycleId: cycleA.id,
      weekNo: 1,
      focus: "Week 1 Foundation",
    });

    // Reject week_no beyond duration
    await expect(
      createWeeklyPlanAuthorized(ctxA, {
        projectId: projectA.id,
        cycleId: cycleA.id,
        weekNo: 13,
      })
    ).rejects.toThrow(/week_no/i);

    // 7. Create valid OKR & Initiative in Project A
    const objectiveA = await createObjectiveAuthorized(ctxA, {
      projectId: projectA.id,
      title: "Objective A",
    });
    const keyResultA = await createKeyResultAuthorized(ctxA, {
      projectId: projectA.id,
      objectiveId: objectiveA.id,
      title: "KR A",
    });
    const initiativeA = await createInitiativeAuthorized(ctxA, {
      projectId: projectA.id,
      keyResultId: keyResultA.id,
      title: "Initiative A",
    });

    // 8. Weekly Commitment in Week 1
    const commitment = await createWeeklyCommitmentAuthorized(ctxA, {
      projectId: projectA.id,
      weeklyPlanId: week1.id,
      initiativeId: initiativeA.id,
      title: "Commitment 1",
    });

    // 9. Unplanned Task (no weekly commitment)
    const draftUnplannedTask = await createTaskAuthorized(ctxA, {
      projectId: projectA.id,
      title: "Inbox Task Without Commitment",
      status: "todo",
    });

    // 10. Direct task transition guard: cannot advance to IN_PROGRESS without commitment
    await expect(
      advanceTaskService(ctxA, {
        projectId: projectA.id,
        taskId: draftUnplannedTask.id,
        status: "IN_PROGRESS",
      })
    ).rejects.toThrow(/weekly commitment/i);

    // 11. Planned Task (with weekly commitment) can advance to IN_PROGRESS
    const plannedTask = await createTaskAuthorized(ctxA, {
      projectId: projectA.id,
      weeklyCommitmentId: commitment.id,
      initiativeId: initiativeA.id,
      title: "Planned Task",
      status: "todo",
    });

    const inProgressTask = await advanceTaskService(ctxA, {
      projectId: projectA.id,
      taskId: plannedTask.id,
      status: "IN_PROGRESS",
    });
    expect(inProgressTask.status).toBe("IN_PROGRESS");

    // 12. getProjectOperatingLoop returns structured hierarchy
    const loop = await getProjectOperatingLoop(ctxA, projectA.id);
    expect(loop.project.id).toBe(projectA.id);
    expect(loop.activeCycle?.id).toBe(cycleA.id);
    expect(loop.currentWeek?.id).toBe(week1.id);
    expect(loop.commitments.length).toBeGreaterThanOrEqual(1);
    expect(loop.objectives.length).toBeGreaterThanOrEqual(1);
    expect(loop.tasks.length).toBeGreaterThanOrEqual(2);
  });
});

// Task 5 (2026-09-14 remediation) — Weekly state machine: CAS trên
// twelveWeekCycles.currentWeek/status + timeline append-only
// cycle_week_events.
describe("Weekly operating-loop state machine (advanceCycleWeekAuthorized)", () => {
  it("materializes exactly durationWeeks empty weekly_plans rows atomically at cycle creation", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Materialize Weeks Project" });

    const cycle = await createCycleAuthorized(ctx, {
      projectId: project.id,
      durationWeeks: 5,
    });

    const rows = await db
      .select()
      .from(schema.weeklyPlans)
      .where(eq(schema.weeklyPlans.cycleId, BigInt(cycle.id)));

    expect(rows).toHaveLength(5);
    expect(rows.map((r) => r.weekNo).sort((a, b) => a - b)).toEqual([1, 2, 3, 4, 5]);
  });

  it("closes week 1 with expectedCurrentWeek=1, moves currentWeek to 2, and appends WEEK_CLOSED + exactly one WEEK_ADVANCED event", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Advance Week Project" });
    const cycle = await createCycleAuthorized(ctx, { projectId: project.id, durationWeeks: 3 });

    const result = await advanceCycleWeekAuthorized(ctx, {
      projectId: project.id,
      cycleId: cycle.id,
      expectedCurrentWeek: 1,
      reflection: "Week 1 done",
      executionScore: 80,
      outcomeScore: 70,
    });

    expect(result.cycle.currentWeek).toBe(2);
    expect(result.cycle.status).toBe("ACTIVE");
    expect(result.week.weekNo).toBe(1);
    expect(result.week.reflection).toBe("Week 1 done");
    expect(result.event.eventType).toBe("WEEK_ADVANCED");

    const events = await db
      .select()
      .from(schema.cycleWeekEvents)
      .where(eq(schema.cycleWeekEvents.cycleId, BigInt(cycle.id)));
    expect(events).toHaveLength(2);
    expect(events.map((e) => e.eventType).sort()).toEqual(["WEEK_ADVANCED", "WEEK_CLOSED"]);
    expect(events.filter((e) => e.eventType === "WEEK_ADVANCED")).toHaveLength(1);
  });

  it("rejects a second command with the same stale expectedCurrentWeek=1 and creates NO event", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Stale CAS Project" });
    const cycle = await createCycleAuthorized(ctx, { projectId: project.id, durationWeeks: 3 });

    await advanceCycleWeekAuthorized(ctx, {
      projectId: project.id,
      cycleId: cycle.id,
      expectedCurrentWeek: 1,
      reflection: "Week 1 done",
    });

    const eventsBefore = await db
      .select()
      .from(schema.cycleWeekEvents)
      .where(eq(schema.cycleWeekEvents.cycleId, BigInt(cycle.id)));
    expect(eventsBefore).toHaveLength(2);

    await expect(
      advanceCycleWeekAuthorized(ctx, {
        projectId: project.id,
        cycleId: cycle.id,
        expectedCurrentWeek: 1,
        reflection: "Stale retry",
      })
    ).rejects.toThrow();

    const eventsAfter = await db
      .select()
      .from(schema.cycleWeekEvents)
      .where(eq(schema.cycleWeekEvents.cycleId, BigInt(cycle.id)));
    expect(eventsAfter).toHaveLength(2);
  });

  it("cannot advance Project B's cycle through Project A's tenant context/projectId", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const projectA = await createProjectService(ctx, { title: "Project A (cross-project guard)" });
    const projectB = await createProjectService(ctx, { title: "Project B (cross-project guard)" });
    const cycleB = await createCycleAuthorized(ctx, { projectId: projectB.id, durationWeeks: 3 });

    await expect(
      advanceCycleWeekAuthorized(ctx, {
        projectId: projectA.id,
        cycleId: cycleB.id,
        expectedCurrentWeek: 1,
        reflection: "Should be rejected",
      })
    ).rejects.toThrow(/not found/i);

    const cycleAfter = await db
      .select()
      .from(schema.twelveWeekCycles)
      .where(eq(schema.twelveWeekCycles.id, BigInt(cycleB.id)));
    expect(cycleAfter[0].currentWeek).toBe(1);

    const events = await db
      .select()
      .from(schema.cycleWeekEvents)
      .where(eq(schema.cycleWeekEvents.cycleId, BigInt(cycleB.id)));
    expect(events).toHaveLength(0);
  });

  it("closing the final week marks the cycle COMPLETED, appends CYCLE_COMPLETED (not WEEK_ADVANCED), and never touches projects.lifecycleStage", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Final Week Project" });
    const cycle = await createCycleAuthorized(ctx, { projectId: project.id, durationWeeks: 1 });

    const [projectBefore] = await db
      .select()
      .from(schema.projects)
      .where(eq(schema.projects.id, BigInt(project.id)));
    expect(projectBefore.lifecycleStage).toBe("P0_DISCOVERY");
    expect(projectBefore.stageVersion).toBe(0);

    const result = await advanceCycleWeekAuthorized(ctx, {
      projectId: project.id,
      cycleId: cycle.id,
      expectedCurrentWeek: 1,
      reflection: "Final week done",
    });

    expect(result.cycle.status).toBe("COMPLETED");
    expect(result.event.eventType).toBe("CYCLE_COMPLETED");

    const events = await db
      .select()
      .from(schema.cycleWeekEvents)
      .where(eq(schema.cycleWeekEvents.cycleId, BigInt(cycle.id)));
    expect(events.map((e) => e.eventType).sort()).toEqual(["CYCLE_COMPLETED", "WEEK_CLOSED"]);
    expect(events.some((e) => e.eventType === "WEEK_ADVANCED")).toBe(false);

    const [projectAfter] = await db
      .select()
      .from(schema.projects)
      .where(eq(schema.projects.id, BigInt(project.id)));
    expect(projectAfter.lifecycleStage).toBe("P0_DISCOVERY");
    expect(projectAfter.stageVersion).toBe(0);
  });

  it("rejects advancing a cycle that is not ACTIVE (already COMPLETED) without creating an event", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Already Completed Project" });
    const cycle = await createCycleAuthorized(ctx, { projectId: project.id, durationWeeks: 1 });

    await advanceCycleWeekAuthorized(ctx, {
      projectId: project.id,
      cycleId: cycle.id,
      expectedCurrentWeek: 1,
      reflection: "Final week done",
    });

    await expect(
      advanceCycleWeekAuthorized(ctx, {
        projectId: project.id,
        cycleId: cycle.id,
        expectedCurrentWeek: 1,
        reflection: "Retry after completion",
      })
    ).rejects.toThrow();

    const events = await db
      .select()
      .from(schema.cycleWeekEvents)
      .where(eq(schema.cycleWeekEvents.cycleId, BigInt(cycle.id)));
    expect(events).toHaveLength(2);
  });
});
