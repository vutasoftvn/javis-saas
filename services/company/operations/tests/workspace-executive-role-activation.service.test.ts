import { describe, it, expect, beforeEach } from "vitest";
import { createTestWorkspaceWithMember, makeTestTenantContext } from "./_helpers";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  getWorkspaceExecutiveRoleStates,
  activateWorkspaceExecutiveRole,
  disableWorkspaceExecutiveRole,
  WorkspaceExecutiveRoleState,
} from "../services/workspace-executive-role-activation.service";
import { createProjectService } from "../services/project.service";
import { activateProjectStartupTeamMember } from "../services/project-startup-team.service";
import { getProjectExecutiveRoleStates } from "../services/executive-role-activation.service";

function roleOf(
  roles: WorkspaceExecutiveRoleState[],
  roleKey: string
): WorkspaceExecutiveRoleState | undefined {
  return roles.find((r) => r.roleKey === roleKey);
}

describe("Workspace Executive Role Activation Service", () => {
  let founderCtx: TenantContext;
  let memberCtx: TenantContext;
  let aiCtx: TenantContext;
  let defaultProjectId: string;

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    defaultProjectId = ws.projectId;
    founderCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: ws.userId,
      membershipRole: "founder",
      isAiAgent: false,
    });
    memberCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: ws.userId,
      membershipRole: "member",
      isAiAgent: false,
    });
    aiCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: ws.userId,
      membershipRole: "founder",
      isAiAgent: true,
    });
  });

  it("lists all 13 roles even when nothing has been activated yet", async () => {
    const board = await getWorkspaceExecutiveRoleStates(founderCtx);
    expect(board.roles).toHaveLength(15);
    // Không role nào bị thiếu khỏi danh sách chỉ vì chưa activate.
    expect(roleOf(board.roles, "cfo")).toBeDefined();
    expect(roleOf(board.roles, "vpe")).toBeDefined();
  });

  it("reports UNAVAILABLE when no Project in the workspace has the underlying agent ACTIVE", async () => {
    // Workspace có Project mặc định nhưng chưa bật profile finance ở đâu cả.
    const board = await getWorkspaceExecutiveRoleStates(founderCtx);
    expect(roleOf(board.roles, "cfo")?.displayState).toBe("UNAVAILABLE");
    expect(roleOf(board.roles, "cfo")?.disabledReason).toBe("UNDERLYING_PROFILE_UNAVAILABLE");
  });

  it("reports AVAILABLE_NOT_ACTIVATED once at least one Project has the underlying agent ACTIVE", async () => {
    await activateProjectStartupTeamMember(founderCtx, defaultProjectId, "finance", {
      expectedVersion: 1,
    });

    const board = await getWorkspaceExecutiveRoleStates(founderCtx);
    expect(roleOf(board.roles, "cfo")?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");
  });

  it("provisions a deployable Workspace Agent when Founder activates the underlying profile", async () => {
    await activateProjectStartupTeamMember(founderCtx, defaultProjectId, "finance", {
      expectedVersion: 1,
    });

    const board = await getProjectExecutiveRoleStates(founderCtx, defaultProjectId);
    expect(board.roles.find((role) => role.roleKey === "cfo")?.workspaceAgentId).toMatch(/^\d+$/);
  });

  it("aggregates availability across Projects — agent ACTIVE in ANY project makes the role available", async () => {
    // Bật finance ở project thứ 2, KHÔNG phải project mặc định. Gate cấp
    // Workspace là OR trên toàn bộ Project nên cfo vẫn phải khả dụng.
    const projectB = await createProjectService(founderCtx, {
      title: "Aggregate Project B",
      creationMode: "ONBOARD_EXISTING",
      initialLifecycleStage: "P0_DISCOVERY",
      initializationRationale: "Test Project B deliberately has no P0 Core bootstrap",
    });
    await activateProjectStartupTeamMember(founderCtx, projectB.id, "finance", {
      expectedVersion: 1,
    });

    const board = await getWorkspaceExecutiveRoleStates(founderCtx);
    expect(roleOf(board.roles, "cfo")?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");
    // marketing chưa bật ở bất kỳ project nào → cmo vẫn UNAVAILABLE.
    expect(roleOf(board.roles, "cmo")?.displayState).toBe("UNAVAILABLE");
  });

  it("activating a role is visible workspace-wide (shared instance, not per-project)", async () => {
    await activateProjectStartupTeamMember(founderCtx, defaultProjectId, "finance", {
      expectedVersion: 1,
    });

    const activated = await activateWorkspaceExecutiveRole(founderCtx, "cfo", {});
    expect(activated.state).toBe("ACTIVE");
    expect(activated.version).toBe(1);

    const board = await getWorkspaceExecutiveRoleStates(founderCtx);
    expect(roleOf(board.roles, "cfo")?.displayState).toBe("ACTIVE");
  });

  it("refuses to activate a role whose underlying agent is not ACTIVE anywhere in the workspace", async () => {
    await expect(activateWorkspaceExecutiveRole(founderCtx, "cfo", {})).rejects.toThrow(
      /EXECUTIVE_ROLE_NOT_AVAILABLE/
    );
  });

  it("permits only a human Founder to activate", async () => {
    await activateProjectStartupTeamMember(founderCtx, defaultProjectId, "finance", {
      expectedVersion: 1,
    });

    await expect(activateWorkspaceExecutiveRole(memberCtx, "cfo", {})).rejects.toThrow(
      /FOUNDER_AUTHORITY_REQUIRED/
    );
    await expect(activateWorkspaceExecutiveRole(aiCtx, "cfo", {})).rejects.toThrow(
      /FOUNDER_AUTHORITY_REQUIRED/
    );
  });

  it("rejects an unknown role key", async () => {
    await expect(activateWorkspaceExecutiveRole(founderCtx, "not_a_role", {})).rejects.toThrow(
      /Invalid roleKey/
    );
  });

  it("disabling a role records disabledReason and flips state back", async () => {
    await activateProjectStartupTeamMember(founderCtx, defaultProjectId, "operations", {
      expectedVersion: 1,
    });

    const activated = await activateWorkspaceExecutiveRole(founderCtx, "coo", {});
    const disabled = await disableWorkspaceExecutiveRole(founderCtx, "coo", {
      expectedVersion: activated.version,
      reason: "not needed yet",
    });
    expect(disabled.state).toBe("DISABLED");
    expect(disabled.version).toBe(activated.version + 1);

    const board = await getWorkspaceExecutiveRoleStates(founderCtx);
    const coo = roleOf(board.roles, "coo");
    expect(coo?.displayState).toBe("DISABLED");
    expect(coo?.disabledReason).toBe("not needed yet");
  });

  it("re-activating after a disable updates the existing row and bumps version (no duplicate row)", async () => {
    await activateProjectStartupTeamMember(founderCtx, defaultProjectId, "operations", {
      expectedVersion: 1,
    });

    const first = await activateWorkspaceExecutiveRole(founderCtx, "coo", {});
    const disabled = await disableWorkspaceExecutiveRole(founderCtx, "coo", {
      expectedVersion: first.version,
      reason: "paused",
    });
    const reactivated = await activateWorkspaceExecutiveRole(founderCtx, "coo", {
      expectedVersion: disabled.version,
    });

    // Cùng một activation row (unique theo workspace+role), version tăng dần.
    expect(reactivated.id).toBe(first.id);
    expect(reactivated.state).toBe("ACTIVE");
    expect(reactivated.version).toBe(disabled.version + 1);

    const board = await getWorkspaceExecutiveRoleStates(founderCtx);
    const coo = roleOf(board.roles, "coo");
    expect(coo?.displayState).toBe("ACTIVE");
    // disabledReason phải được xoá khi bật lại, không để rò rỉ lý do cũ.
    expect(coo?.disabledReason).toBeUndefined();
  });

  it("enforces optimistic locking on both activate and disable", async () => {
    await activateProjectStartupTeamMember(founderCtx, defaultProjectId, "operations", {
      expectedVersion: 1,
    });

    const activated = await activateWorkspaceExecutiveRole(founderCtx, "coo", {});

    await expect(
      disableWorkspaceExecutiveRole(founderCtx, "coo", { expectedVersion: 999 })
    ).rejects.toThrow(/CAS_CONFLICT/);

    await disableWorkspaceExecutiveRole(founderCtx, "coo", {
      expectedVersion: activated.version,
    });

    await expect(
      activateWorkspaceExecutiveRole(founderCtx, "coo", { expectedVersion: 999 })
    ).rejects.toThrow(/CAS_CONFLICT/);
  });

  it("rejects a mismatched expectedVersion on the very first activation, in both directions", async () => {
    await activateProjectStartupTeamMember(founderCtx, defaultProjectId, "operations", {
      expectedVersion: 1,
    });

    // Board báo version 1 cho role chưa activate → chỉ 1 là hợp lệ.
    await expect(
      activateWorkspaceExecutiveRole(founderCtx, "coo", { expectedVersion: 2 })
    ).rejects.toThrow(/CAS_CONFLICT/);
    await expect(
      activateWorkspaceExecutiveRole(founderCtx, "coo", { expectedVersion: 0 })
    ).rejects.toThrow(/CAS_CONFLICT/);

    const ok = await activateWorkspaceExecutiveRole(founderCtx, "coo", { expectedVersion: 1 });
    expect(ok.state).toBe("ACTIVE");
  });

  it("refuses to disable a role that was never activated in this workspace", async () => {
    await expect(disableWorkspaceExecutiveRole(founderCtx, "cro", {})).rejects.toThrow(
      /never activated|not found/i
    );
  });
});
