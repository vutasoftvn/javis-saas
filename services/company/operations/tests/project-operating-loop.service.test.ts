import { describe, it, expect, beforeEach } from "vitest";
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
