import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import { createProjectService } from "../services/project.service";
import { MVP_CAPABILITY_BY_ID } from "../../shared/contracts/mvp-surface.generated";
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

// Step 3 — mọi route thật handler đã export (key-results, initiatives,
// task-status PATCH) PHẢI có 1 entry canonical trong mvp-surface.json. Test
// này là "drift detector": trước khi đăng ký entry, nó đỏ (route invisible
// với contract); sau khi đăng ký + regenerate, nó xanh.
describe("project-operating-loop contract completeness (mvp-surface registration)", () => {
  it("registers POST .../operating-loop/key-results as a canonical capability", () => {
    const cap = MVP_CAPABILITY_BY_ID.get("project.key_result.write");
    expect(cap).toBeDefined();
    expect(cap?.method).toBe("POST");
    expect(cap?.path).toBe("/operations/projects/:projectId/operating-loop/key-results");
    expect(cap?.requiresProject).toBe(true);
  });

  it("registers POST .../operating-loop/initiatives as a canonical capability", () => {
    const cap = MVP_CAPABILITY_BY_ID.get("project.initiative.write");
    expect(cap).toBeDefined();
    expect(cap?.method).toBe("POST");
    expect(cap?.path).toBe("/operations/projects/:projectId/operating-loop/initiatives");
    expect(cap?.requiresProject).toBe(true);
  });

  it("registers PATCH .../operating-loop/tasks/:taskId/status as a canonical capability", () => {
    const cap = MVP_CAPABILITY_BY_ID.get("project.task.status.write");
    expect(cap).toBeDefined();
    expect(cap?.method).toBe("PATCH");
    expect(cap?.path).toBe("/operations/projects/:projectId/operating-loop/tasks/:taskId/status");
    expect(cap?.requiresProject).toBe(true);
  });
});

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

  it("returns the exact canonical response shape from getProjectOperatingLoopApi", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const project = await createProjectService(
      {
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test",
      } as any,
      { title: "Shape Project" }
    );

    const objective = await createObjectiveApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      title: "Objective",
    });
    const kr = await createKeyResultApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      objectiveId: objective.id,
      title: "KR",
    });
    const initiative = await createInitiativeApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      keyResultId: kr.id,
      title: "Initiative",
    });
    const cycle = await createCycleApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      durationWeeks: 12,
    });
    const week = await createWeeklyPlanApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      cycleId: cycle.id,
      weekNo: 1,
    });
    const commitment = await createWeeklyCommitmentApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      weeklyPlanId: week.id,
      initiativeId: initiative.id,
      title: "Commitment",
    });
    const task = await createTaskApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      weeklyCommitmentId: commitment.id,
      initiativeId: initiative.id,
      title: "Task",
    });

    const loop = await getProjectOperatingLoopApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
    });

    expect(loop).toMatchObject({
      project: { id: project.id, lifecycleStage: "P0_DISCOVERY", stageVersion: 0 },
      objectives: [
        {
          objective: { id: objective.id },
          keyResults: [{ keyResult: { id: kr.id }, initiatives: [{ id: initiative.id }] }],
        },
      ],
      activeCycle: { id: cycle.id, currentWeek: 1 },
      currentWeek: { weekNo: 1 },
      commitments: [{ weeklyPlanId: week.id }],
      tasks: [{ projectId: project.id }],
    });

    // Task 3 Step 4 — task denormalizes weeklyPlanId/keyResultId from the
    // commitment/initiative it was created against; DTO must surface both.
    expect(loop.tasks[0]).toMatchObject({
      id: task.id,
      weeklyPlanId: week.id,
      keyResultId: kr.id,
    });
  });

  it("resolves keyResultId via the weekly commitment's own initiative when no initiativeId is passed on the task (fallback branch, not purposeType=KR)", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const project = await createProjectService(
      {
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test",
      } as any,
      { title: "Fallback KR Resolution Project" }
    );

    const objective = await createObjectiveApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      title: "Objective",
    });
    const kr = await createKeyResultApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      objectiveId: objective.id,
      title: "KR",
    });
    const initiative = await createInitiativeApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      keyResultId: kr.id,
      title: "Initiative carrying the KR link",
    });
    const cycle = await createCycleApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      durationWeeks: 12,
    });
    const week = await createWeeklyPlanApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      cycleId: cycle.id,
      weekNo: 1,
    });
    // purposeType deliberately NOT "KR" (and no purposeRef) — the only way to
    // reach keyResultId is through the commitment's own initiativeId, not
    // through purposeRef.
    const commitment = await createWeeklyCommitmentApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      weeklyPlanId: week.id,
      initiativeId: initiative.id,
      title: "Commitment without explicit KR purpose",
      purposeType: "GENERAL",
    });

    // Task created with weeklyCommitmentId ONLY — no initiativeId passed.
    const task = await createTaskApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      weeklyCommitmentId: commitment.id,
      title: "Task inferring KR through commitment's own initiative",
    });

    expect((task as any).weeklyPlanId).toBe(week.id);
    expect((task as any).keyResultId).toBe(kr.id);
  });

  it("Objective body accepts `why` and does not surface the legacy client-only key `description`", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const project = await createProjectService(
      {
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test",
      } as any,
      { title: "Body Shape Project" }
    );

    const objective = await createObjectiveApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      title: "Objective with why",
      why: "Vì đây là ưu tiên số 1",
      // Legacy client-only key from an older contract draft — must be a
      // silent no-op, not a stored field (no documented compat decision to
      // keep it).
      ...({ description: "legacy client field" } as any),
    });

    expect(objective.why).toBe("Vì đây là ưu tiên số 1");
    expect((objective as any).description).toBeUndefined();
  });

  it("Weekly commitment body accepts `plannedEffort` and does not surface the legacy client-only key `targetConfidence`", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const project = await createProjectService(
      {
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "admin",
        permissions: [],
        correlationId: "test",
      } as any,
      { title: "Commitment Body Shape Project" }
    );
    const cycle = await createCycleApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      durationWeeks: 12,
    });
    const week = await createWeeklyPlanApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      cycleId: cycle.id,
      weekNo: 1,
    });

    const commitment = await createWeeklyCommitmentApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      weeklyPlanId: week.id,
      title: "Commitment with plannedEffort",
      plannedEffort: "HIGH",
      // Legacy client-only key from an older contract draft — must be a
      // silent no-op, not a stored field (no documented compat decision to
      // keep it).
      ...({ targetConfidence: 0.9 } as any),
    });

    expect(commitment.plannedEffort).toBe("HIGH");
    expect((commitment as any).targetConfidence).toBeUndefined();
  });
});
