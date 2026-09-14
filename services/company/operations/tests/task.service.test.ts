import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import type { TenantContext } from "../../shared/types/tenant_context";
import { createProjectService } from "../services/project.service";
import {
  createTaskService,
  getTaskService,
  deleteTaskService,
  createAiTaskProposalService,
  CreateTaskParams,
  CreateAiTaskProposalParams,
} from "../services/task.service";
import {
  createCycleAuthorized,
  createWeeklyPlanAuthorized,
  createWeeklyCommitmentAuthorized,
  createObjectiveAuthorized,
  createKeyResultAuthorized,
  createInitiativeAuthorized,
  advanceTaskService,
} from "../services/project-operating-loop.service";

function ctxFor(workspaceId: string, userId = "1"): TenantContext {
  return Object.freeze({
    workspaceId,
    userId,
    workforceMemberId: userId,
    membershipRole: "founder",
    permissions: [],
    correlationId: "test-task-delete",
    platformUserId: null,
  }) as unknown as TenantContext;
}

describe("deleteTaskService (soft delete)", () => {
  it("marks the task deletedAt and excludes it from subsequent getTaskService", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Delete Task Test" });
    const task = await createTaskService(
      { workspaceId: ws.workspaceId, title: "To be deleted", projectId: project.id },
      ws.bearerToken
    );

    const result = await deleteTaskService(task.id, ctx);
    expect(result.id).toBe(task.id);
    expect(result.deletedAt).toBeTruthy();

    await expect(getTaskService(task.id, ctx)).rejects.toThrow();
  });
});

describe("createTaskService week/kr denormalization", () => {
  it("fills weeklyPlanId and keyResultId when created with a weeklyCommitmentId", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Denorm Test Project" });

    const cycle = await createCycleAuthorized(ctx, {
      projectId: project.id,
      durationWeeks: 12,
    });
    const week1 = await createWeeklyPlanAuthorized(ctx, {
      projectId: project.id,
      cycleId: cycle.id,
      weekNo: 1,
    });
    const objective = await createObjectiveAuthorized(ctx, {
      projectId: project.id,
      title: "Objective for denorm test",
    });
    const keyResult = await createKeyResultAuthorized(ctx, {
      projectId: project.id,
      objectiveId: objective.id,
      title: "KR for denorm test",
    });
    const commitment = await createWeeklyCommitmentAuthorized(ctx, {
      projectId: project.id,
      weeklyPlanId: week1.id,
      title: "Commitment for denorm test",
      purposeType: "KR",
      purposeRef: keyResult.id,
    });

    const task = await createTaskService(
      {
        workspaceId: ws.workspaceId,
        projectId: project.id,
        title: "Task linked to weekly commitment",
        weeklyCommitmentId: commitment.id,
      },
      ws.bearerToken
    );

    expect(task.weeklyPlanId).toBe(week1.id);
    expect(task.keyResultId).toBe(keyResult.id);

    // getTaskService phải trả về cùng giá trị denormalize đã lưu, không chỉ
    // response của lệnh tạo.
    const reloaded = await getTaskService(task.id, ctx);
    expect(reloaded.weeklyPlanId).toBe(week1.id);
    expect(reloaded.keyResultId).toBe(keyResult.id);
  });

  it("fills keyResultId from initiative when created without a weeklyCommitmentId", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Denorm Initiative Project" });

    const objective = await createObjectiveAuthorized(ctx, {
      projectId: project.id,
      title: "Objective for initiative denorm test",
    });
    const keyResult = await createKeyResultAuthorized(ctx, {
      projectId: project.id,
      objectiveId: objective.id,
      title: "KR for initiative denorm test",
    });
    const initiative = await createInitiativeAuthorized(ctx, {
      projectId: project.id,
      keyResultId: keyResult.id,
      title: "Initiative for denorm test",
    });

    const task = await createTaskService(
      {
        workspaceId: ws.workspaceId,
        projectId: project.id,
        title: "Task linked directly to initiative",
        initiativeId: initiative.id,
      },
      ws.bearerToken
    );

    expect(task.weeklyPlanId).toBeUndefined();
    expect(task.keyResultId).toBe(keyResult.id);
  });
});

describe("Task mutations locked to their exact Project (2026-09-14 remediation)", () => {
  async function setupTwoProjects() {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const projectA = await createProjectService(ctx, { title: "Project A" });
    const projectB = await createProjectService(ctx, { title: "Project B" });

    // Dựng đủ chuỗi OKR → cycle → week → commitment trong Project B để có một
    // weeklyCommitment thật sự thuộc B.
    const objectiveB = await createObjectiveAuthorized(ctx, { projectId: projectB.id, title: "Objective B" });
    const keyResultB = await createKeyResultAuthorized(ctx, {
      projectId: projectB.id,
      objectiveId: objectiveB.id,
      title: "KR B",
    });
    const initiativeB = await createInitiativeAuthorized(ctx, {
      projectId: projectB.id,
      keyResultId: keyResultB.id,
      title: "Initiative B",
    });
    const cycleB = await createCycleAuthorized(ctx, { projectId: projectB.id, durationWeeks: 12 });
    const weekB = await createWeeklyPlanAuthorized(ctx, {
      projectId: projectB.id,
      cycleId: cycleB.id,
      weekNo: 1,
    });
    const commitmentB = await createWeeklyCommitmentAuthorized(ctx, {
      projectId: projectB.id,
      weeklyPlanId: weekB.id,
      initiativeId: initiativeB.id,
      title: "Commitment B",
    });
    const taskB = await createTaskService(
      {
        workspaceId: ws.workspaceId,
        projectId: projectB.id,
        title: "Task B",
        weeklyCommitmentId: commitmentB.id,
      },
      ws.bearerToken
    );

    return { ws, ctx, projectA, projectB, initiativeB, commitmentB, taskB };
  }

  it("rejects createTaskService when weeklyCommitmentId belongs to a different Project", async () => {
    const { ws, projectA, commitmentB } = await setupTwoProjects();

    await expect(
      createTaskService(
        {
          workspaceId: ws.workspaceId,
          projectId: projectA.id,
          weeklyCommitmentId: commitmentB.id,
          title: "Cross-project via commitment",
        },
        ws.bearerToken
      )
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects createTaskService when initiativeId belongs to a different Project", async () => {
    const { ws, projectA, initiativeB } = await setupTwoProjects();

    await expect(
      createTaskService(
        {
          workspaceId: ws.workspaceId,
          projectId: projectA.id,
          initiativeId: initiativeB.id,
          title: "Cross-project via initiative",
        },
        ws.bearerToken
      )
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects createTaskService without a projectId (PROJECT_CONTEXT_REQUIRED) — never selects the first Project", async () => {
    const ws = await createTestWorkspaceWithMember();

    await expect(
      createTaskService(
        {
          workspaceId: ws.workspaceId,
          title: "No project context",
        } as CreateTaskParams,
        ws.bearerToken
      )
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects createAiTaskProposalService without a projectId (PROJECT_CONTEXT_REQUIRED) — never selects the first Project", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);

    await expect(
      createAiTaskProposalService(
        {
          workspaceId: ws.workspaceId,
          title: "No project context proposal",
          proposedByAgentInstanceId: "agent_test",
          contract: {
            outcomeType: "BAU",
            expectedOutcome: "n/a",
            acceptanceCriteria: {},
            expectedEvidenceRefs: [],
            impactHypothesis: "n/a",
          },
        } as unknown as CreateAiTaskProposalParams,
        ctx
      )
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("rejects advanceTaskService (project-operating-loop) when the task belongs to a different Project — not_found, not leaked across Projects", async () => {
    const { ctx, projectA, taskB } = await setupTwoProjects();

    await expect(
      advanceTaskService(ctx, {
        projectId: projectA.id,
        taskId: taskB.id,
        status: "DONE",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });
});
