import { describe, it, expect } from "vitest";
import { db, schema } from "../models/db";
import { createTestWorkspaceWithMember } from "./_helpers";
import type { TenantContext } from "../../shared/types/tenant_context";
import { createProjectService } from "../services/project.service";
import {
  transitionProjectLifecycle,
  listProjectLifecycleEvents,
} from "../services/project-lifecycle.service";
import { getProjectExecutiveRoleStates } from "../services/executive-role-activation.service";

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

describe("createProjectService onboarding modes (2026-09-14 remediation)", () => {
  it("NEW ignores any stage input; persisted baseline is always P0 with no lifecycle event", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);

    const project = await createProjectService(ctx, { title: "Greenfield", creationMode: "NEW" });
    expect(project.lifecycleStage).toBe("P0_DISCOVERY");
    expect(project.stageVersion).toBe(0);

    const events = await listProjectLifecycleEvents(ctx, project.id);
    expect(events.items).toHaveLength(0);
  });

  it("defaults to NEW/P0 when creationMode is omitted entirely", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);

    const project = await createProjectService(ctx, { title: "No mode given" });
    expect(project.lifecycleStage).toBe("P0_DISCOVERY");
    expect(project.stageVersion).toBe(0);
  });

  it("keeps a member-created P0 Project compatible without silently activating P0 Core", async () => {
    const ws = await createTestWorkspaceWithMember();
    const founderCtx = ctxFor(ws.workspaceId, ws.userId);
    const memberCtx = ctxFor(ws.workspaceId, ws.userId, "member");

    const project = await createProjectService(memberCtx, { title: "Member-created P0" });
    const board = await getProjectExecutiveRoleStates(founderCtx, project.id);
    expect(board.roles.find((role) => role.roleKey === "cfo")?.effectiveState).toBe(
      "OFFICE_DISABLED"
    );
  });

  it("ONBOARD_EXISTING lets a Founder state the real current stage exactly once, with an honest PROJECT_INITIALIZED event", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);

    const project = await createProjectService(ctx, {
      title: "Existing business",
      creationMode: "ONBOARD_EXISTING",
      initialLifecycleStage: "P4_GO_TO_MARKET",
      initializationRationale: "Founder attests product is already in market",
    });

    expect(project.lifecycleStage).toBe("P4_GO_TO_MARKET");
    expect(project.stageVersion).toBe(1);

    const events = await listProjectLifecycleEvents(ctx, project.id);
    expect(events.items).toHaveLength(1);
    expect(events.items[0]).toMatchObject({
      fromStage: null,
      toStage: "P4_GO_TO_MARKET",
      fromStageVersion: 0,
      eventType: "PROJECT_INITIALIZED",
      initializationSource: "FOUNDER_ONBOARDING",
      rationale: "Founder attests product is already in market",
    });
  });

  it("a normal transition after ONBOARD_EXISTING still requires the correct expectedStageVersion (1, not 0)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, {
      title: "Existing business transitions",
      creationMode: "ONBOARD_EXISTING",
      initialLifecycleStage: "P4_GO_TO_MARKET",
      initializationRationale: "Founder attests product is already in market",
    });

    await expect(
      transitionProjectLifecycle(ctx, project.id, {
        toStage: "P5_OPERATE_GROWTH",
        expectedStageVersion: 0,
      })
    ).rejects.toThrow(/changed; reload/i);

    const res = await transitionProjectLifecycle(ctx, project.id, {
      toStage: "P5_OPERATE_GROWTH",
      expectedStageVersion: 1,
    });
    expect(res).toMatchObject({ lifecycleStage: "P5_OPERATE_GROWTH", stageVersion: 2 });

    // Chuỗi event vẫn append-only: 1 PROJECT_INITIALIZED + 1 TRANSITION, không
    // ghi đè hay xoá event khai báo baseline.
    const events = await listProjectLifecycleEvents(ctx, project.id);
    expect(events.items).toHaveLength(2);
    expect(events.items[0].eventType).toBe("PROJECT_INITIALIZED");
    expect(events.items[1]).toMatchObject({ eventType: "TRANSITION", fromStage: "P4_GO_TO_MARKET" });
  });

  it("denies ONBOARD_EXISTING for a member without Founder/co-founder/admin authority", async () => {
    const ws = await createTestWorkspaceWithMember();
    const memberCtx = ctxFor(ws.workspaceId, ws.userId, "member");

    await expect(
      createProjectService(memberCtx, {
        title: "Unauthorized onboarding",
        creationMode: "ONBOARD_EXISTING",
        initialLifecycleStage: "P4_GO_TO_MARKET",
        initializationRationale: "should not be allowed",
      })
    ).rejects.toThrow(/founder|admin|privilege/i);
  });

  it("rejects ONBOARD_EXISTING with a missing rationale", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);

    await expect(
      createProjectService(ctx, {
        title: "No rationale",
        creationMode: "ONBOARD_EXISTING",
        initialLifecycleStage: "P4_GO_TO_MARKET",
      })
    ).rejects.toThrow(/rationale/i);

    await expect(
      createProjectService(ctx, {
        title: "Blank rationale",
        creationMode: "ONBOARD_EXISTING",
        initialLifecycleStage: "P4_GO_TO_MARKET",
        initializationRationale: "   ",
      })
    ).rejects.toThrow(/rationale/i);
  });

  it("rejects ONBOARD_EXISTING with an invalid stage", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);

    await expect(
      createProjectService(ctx, {
        title: "Bogus stage",
        creationMode: "ONBOARD_EXISTING",
        // initialLifecycleStage là string ở boundary (giống toStage) — validate
        // runtime theo PROJECT_LIFECYCLE_STAGES, không phải lỗi biên dịch.
        initialLifecycleStage: "P99_MADE_UP",
        initializationRationale: "attempted history rewrite",
      })
    ).rejects.toThrow(/initialLifecycleStage/i);
  });

  it("refuses a second baseline declaration for an already-initialized project: only lifecycle transition can move it further, and re-declaring the same stage is rejected", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, {
      title: "Existing business, no re-baseline",
      creationMode: "ONBOARD_EXISTING",
      initialLifecycleStage: "P4_GO_TO_MARKET",
      initializationRationale: "Founder attests product is already in market",
    });

    // ONBOARD_EXISTING không có khái niệm "target một project đã tồn tại" —
    // createProjectService luôn insert row mới. Sau khi baseline đã ghi, cách
    // DUY NHẤT để đổi stage là transitionProjectLifecycle (CAS), và transition
    // đó tự chặn một lần "khai báo lại" cùng stage hiện tại — không có đường
    // nào để ghi thêm một event PROJECT_INITIALIZED thứ hai cho cùng project.
    await expect(
      transitionProjectLifecycle(ctx, project.id, {
        toStage: "P4_GO_TO_MARKET",
        expectedStageVersion: 1,
      })
    ).rejects.toThrow(/already at the requested lifecycle stage/i);

    const events = await listProjectLifecycleEvents(ctx, project.id);
    expect(events.items.filter((e) => e.eventType === "PROJECT_INITIALIZED")).toHaveLength(1);
  });
});
