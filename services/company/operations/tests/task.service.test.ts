import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import type { TenantContext } from "../../shared/types/tenant_context";
import { createProjectService } from "../services/project.service";
import { createTaskService, getTaskService, deleteTaskService } from "../services/task.service";
import {
  createCycleAuthorized,
  createWeeklyPlanAuthorized,
  createWeeklyCommitmentAuthorized,
  createObjectiveAuthorized,
  createKeyResultAuthorized,
  createInitiativeAuthorized,
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
