import { describe, it, expect } from "vitest";
import { db, schema } from "../models/db";
import { createTestWorkspaceWithMember } from "./_helpers";
import type { TenantContext } from "../../shared/types/tenant_context";
import { createProjectService } from "../services/project.service";
import {
  transitionProjectLifecycle,
  listProjectLifecycleEvents,
} from "../services/project-lifecycle.service";

function ctxFor(
  workspaceId: string,
  userId = "1",
  membershipRole = "founder"
): TenantContext {
  return Object.freeze({
    workspaceId,
    userId,
    workforceMemberId: userId,
    membershipRole,
    permissions: [],
    correlationId: "test-project-lifecycle",
    platformUserId: null,
  }) as unknown as TenantContext;
}

describe("project lifecycle transition (no framework gate, human-only)", () => {
  it("advances one stage with optimistic locking and appends an immutable event", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Lifecycle P" });

    const res = await transitionProjectLifecycle(ctx, project.id, {
      toStage: "P1_PROBLEM_VALIDATION",
      expectedStageVersion: 0,
      rationale: "validated interviews",
    });
    expect(res).toMatchObject({ lifecycleStage: "P1_PROBLEM_VALIDATION", stageVersion: 1 });

    const events = await listProjectLifecycleEvents(ctx, project.id);
    expect(events.items).toHaveLength(1);
    expect(events.items[0]).toMatchObject({
      fromStage: "P0_DISCOVERY",
      toStage: "P1_PROBLEM_VALIDATION",
      fromStageVersion: 0,
    });
  });

  it("rejects a stale expectedStageVersion", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Lifecycle stale" });

    await transitionProjectLifecycle(ctx, project.id, {
      toStage: "P1_PROBLEM_VALIDATION",
      expectedStageVersion: 0,
    });

    await expect(
      transitionProjectLifecycle(ctx, project.id, {
        toStage: "P2_SOLUTION_VALIDATION",
        expectedStageVersion: 0,
      })
    ).rejects.toThrow(/changed; reload/i);
  });

  it("rejects skipping more than one stage forward", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Lifecycle skip" });

    await expect(
      transitionProjectLifecycle(ctx, project.id, {
        toStage: "P3_BUILD_VALIDATE",
        expectedStageVersion: 0,
      })
    ).rejects.toThrow(/at most one stage/i);
  });

  it("requires a rationale to move backward", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Lifecycle back" });

    await transitionProjectLifecycle(ctx, project.id, {
      toStage: "P1_PROBLEM_VALIDATION",
      expectedStageVersion: 0,
    });

    await expect(
      transitionProjectLifecycle(ctx, project.id, {
        toStage: "P0_DISCOVERY",
        expectedStageVersion: 1,
      })
    ).rejects.toThrow(/rationale/i);

    const ok = await transitionProjectLifecycle(ctx, project.id, {
      toStage: "P0_DISCOVERY",
      expectedStageVersion: 1,
      rationale: "pivot",
    });
    expect(ok.lifecycleStage).toBe("P0_DISCOVERY");
  });

  it("denies transition for a non-privileged member", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Lifecycle perm" });

    const memberCtx = ctxFor(ws.workspaceId, ws.userId, "member");
    await expect(
      transitionProjectLifecycle(memberCtx, project.id, {
        toStage: "P1_PROBLEM_VALIDATION",
        expectedStageVersion: 0,
      })
    ).rejects.toThrow(/founder|admin|privilege/i);
  });

  it("does not leak a project from another workspace", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createTestWorkspaceWithMember();
    const ctxA = ctxFor(wsA.workspaceId, wsA.userId);
    const ctxB = ctxFor(wsB.workspaceId, wsB.userId);
    const projectB = await createProjectService(ctxB, { title: "B only" });

    await expect(
      transitionProjectLifecycle(ctxA, projectB.id, {
        toStage: "P1_PROBLEM_VALIDATION",
        expectedStageVersion: 0,
      })
    ).rejects.toThrow(/not found/i);
  });
});
