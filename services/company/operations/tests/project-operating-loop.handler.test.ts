import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import { createProjectService } from "../services/project.service";
import {
  getProjectOperatingLoopApi,
  createObjectiveApi,
  createKeyResultApi,
  createInitiativeApi,
  createCycleApi,
  createWeeklyPlanApi,
  createWeeklyCommitmentApi,
  createTaskApi,
  advanceTaskApi,
} from "../handlers/project-operating-loop.handler";

describe("project-operating-loop handler authorization & tenant boundaries", () => {
  it("rejects unauthenticated requests (missing bearer)", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    await expect(
      getProjectOperatingLoopApi({
        authorization: undefined,
        workspaceId: ws.workspaceId,
        projectId: "123",
      })
    ).rejects.toThrow(/unauthenticated|authorization|token/i);
  });

  it("rejects token when caller is not a member of the workspace (permission denied)", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "founder" });
    const wsB = await createTestWorkspaceWithMember({ role: "founder" });

    await expect(
      getProjectOperatingLoopApi({
        authorization: wsB.bearerToken,
        workspaceId: wsA.workspaceId,
        projectId: "123",
      })
    ).rejects.toThrow(/không thuộc workspace|permission|access|denied/i);
  });

  it("rejects accessing a project belonging to another workspace (notFound)", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "founder" });
    const wsB = await createTestWorkspaceWithMember({ role: "founder" });

    // Project B belongs to Workspace B
    const projectB = await createProjectService(
      {
        workspaceId: wsB.workspaceId,
        userId: wsB.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test",
      } as any,
      { title: "Secret Project B" }
    );

    // Member A attempts to get Project B's loop using Workspace A header
    await expect(
      getProjectOperatingLoopApi({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        projectId: projectB.id,
      })
    ).rejects.toThrow(/not found/i);
  });

  it("executes the full operating-loop flow through public endpoints when authorized", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const project = await createProjectService(
      {
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test",
      } as any,
      { title: "Alpha Project" }
    );

    // 1. Create Objective
    const objective = await createObjectiveApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      title: "Land 10 Customers",
    });
    expect(objective.title).toBe("Land 10 Customers");

    // 2. Create Key Result
    const kr = await createKeyResultApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      objectiveId: objective.id,
      title: "Reach 10 paid signups",
      targetValue: 10,
    });
    expect(kr.targetValue).toBe(10);

    // 3. Create Initiative
    const initiative = await createInitiativeApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      keyResultId: kr.id,
      title: "Cold outreach campaign",
    });
    expect(initiative.title).toBe("Cold outreach campaign");

    // 4. Create Cycle (duration 1..12)
    const cycle = await createCycleApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      theme: "First Traction",
      durationWeeks: 12,
    });
    expect(cycle.durationWeeks).toBe(12);

    // 5. Conflict: cannot create second active cycle
    await expect(
      createCycleApi({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        projectId: project.id,
        theme: "Second Active Cycle",
        durationWeeks: 6,
      })
    ).rejects.toThrow(/active/i);

    // 6. Create Weekly Plan
    const week = await createWeeklyPlanApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      cycleId: cycle.id,
      weekNo: 1,
      focus: "Build outreach list",
    });
    expect(week.weekNo).toBe(1);

    // 7. Create Weekly Commitment
    const commitment = await createWeeklyCommitmentApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      weeklyPlanId: week.id,
      initiativeId: initiative.id,
      title: "Send 50 personalized emails",
    });
    expect(commitment.title).toBe("Send 50 personalized emails");

    // 8. Create Task with Commitment
    const task = await createTaskApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      weeklyCommitmentId: commitment.id,
      initiativeId: initiative.id,
      title: "Scrape lead list",
    });
    expect(task.title).toBe("Scrape lead list");

    // 9. Advance Task
    const advanced = await advanceTaskApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      taskId: task.id,
      status: "IN_PROGRESS",
    });
    expect(advanced.status).toBe("IN_PROGRESS");

    // 10. Get full operating loop
    const loop = await getProjectOperatingLoopApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
    });
    expect(loop.project.id).toBe(project.id);
    expect(loop.activeCycle?.id).toBe(cycle.id);
    expect(loop.currentWeek?.id).toBe(week.id);
    expect(loop.commitments).toHaveLength(1);
    expect(loop.objectives).toHaveLength(1);
    expect(loop.objectives[0].keyResults).toHaveLength(1);
    expect(loop.objectives[0].keyResults[0].initiatives).toHaveLength(1);
    expect(loop.tasks).toHaveLength(1);
  });
});
