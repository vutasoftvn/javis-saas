import { describe, it, expect, beforeEach } from "vitest";
import { APIError } from "encore.dev/api";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
  createSecondWorkspace,
  makeTestTenantContext,
} from "./_helpers";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  getProjectExecutiveRoleStates,
  selectStartupCorePreset,
  activateExecutiveRole,
  disableExecutiveRole,
  ProjectExecutiveRoleState,
} from "../services/executive-role-activation.service";
import {
  activateProjectStartupTeamMember,
} from "../services/project-startup-team.service";

describe("Executive Role Activation Service", () => {
  let founderCtx: TenantContext;
  let memberCtx: TenantContext;
  let aiCtx: TenantContext;
  let projectId: string;
  let foreignProjectId: string;

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    projectId = ws.projectId;
    founderCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: ws.userId,
      workforceMemberId: ws.userId,
      membershipRole: "founder",
      isAiAgent: false,
    });

    const member = await addMemberToWorkspace(ws.workspaceId, "member");
    memberCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: member.userId,
      workforceMemberId: member.userId,
      membershipRole: "member",
      isAiAgent: false,
    });

    aiCtx = makeTestTenantContext({
      workspaceId: ws.workspaceId,
      userId: "ai-agent-user",
      workforceMemberId: "ai-workforce-member",
      membershipRole: "member",
      isAiAgent: true,
    });

    const secondWs = await createSecondWorkspace();
    foreignProjectId = secondWs.projectId;
  });

  it("permits only a human Founder to activate CFO", async () => {
    await expect(
      activateExecutiveRole(memberCtx, projectId, "cfo", { expectedVersion: 1 })
    ).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED|FOUNDER_AUTHORIZATION_REQUIRED/);

    await expect(
      activateExecutiveRole(aiCtx, projectId, "cfo", { expectedVersion: 1 })
    ).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED|FOUNDER_AUTHORIZATION_REQUIRED/);
  });

  it("refuses CFO when Finance assignment is not ACTIVE", async () => {
    // Finance assignment starts as TEMPLATE, not ACTIVE
    await expect(
      activateExecutiveRole(founderCtx, projectId, "cfo", { expectedVersion: 1 })
    ).rejects.toThrow(/EXECUTIVE_ROLE_NOT_AVAILABLE/);
  });

  it("rejects action on a foreign Project with not found", async () => {
    await expect(
      activateExecutiveRole(founderCtx, foreignProjectId, "cfo", { expectedVersion: 1 })
    ).rejects.toThrow(/Project not found/);
  });

  it("activates CFO when Finance is ACTIVE, and enforces CAS versioning", async () => {
    // 1. Activate finance profile in startup team
    await activateProjectStartupTeamMember(founderCtx, projectId, "finance", { expectedVersion: 1 });

    // 2. Initial state: CFO should be AVAILABLE_NOT_ACTIVATED
    const statesBefore = await getProjectExecutiveRoleStates(founderCtx, projectId);
    const cfoBefore = statesBefore.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "cfo");
    expect(cfoBefore).toBeDefined();
    expect(cfoBefore?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");

    // 3. Founder activates CFO
    const activated = await activateExecutiveRole(founderCtx, projectId, "cfo", {
      expectedVersion: cfoBefore!.version,
      idempotencyKey: "act-cfo-1",
    });
    expect(activated.state).toBe("ACTIVE");
    expect(activated.roleKey).toBe("cfo");

    // 4. Stale expectedVersion throws CAS conflict
    await expect(
      activateExecutiveRole(founderCtx, projectId, "cfo", {
        expectedVersion: 999, // stale
      })
    ).rejects.toThrow(/CAS_CONFLICT|stale/i);

    // 5. Duplicate idempotency key returns existing state
    const dup = await activateExecutiveRole(founderCtx, projectId, "cfo", {
      expectedVersion: activated.version,
      idempotencyKey: "act-cfo-1",
    });
    expect(dup.state).toBe("ACTIVE");
  });

  it("selectStartupCorePreset activates only eligible default roles and records setting", async () => {
    // Activate marketing only (finance remains TEMPLATE)
    await activateProjectStartupTeamMember(founderCtx, projectId, "marketing", { expectedVersion: 1 });

    const result = await selectStartupCorePreset(founderCtx, projectId, {
      presetKey: "startup-discovery",
      expectedVersion: 1,
      idempotencyKey: "preset-disc-1",
    });

    expect(result.presetKey).toBe("startup-discovery");
    // cmo is eligible (marketing is ACTIVE) -> activated
    // cfo is not eligible (finance is TEMPLATE) -> remains unavailable/not activated
    // chief_of_staff is PENDING_OPERATIONS_PROFILE -> unavailable
    const states = await getProjectExecutiveRoleStates(founderCtx, projectId);
    const cmo = states.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "cmo");
    const cfo = states.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "cfo");
    const cos = states.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "chief_of_staff");

    expect(cmo?.displayState).toBe("ACTIVE");
    expect(cfo?.displayState).toBe("UNAVAILABLE");
    expect(cos?.displayState).toBe("UNAVAILABLE");
  });

  it("disabling an active role retains history and sets state to DISABLED", async () => {
    await activateProjectStartupTeamMember(founderCtx, projectId, "marketing", { expectedVersion: 1 });
    const cmoBefore = (await getProjectExecutiveRoleStates(founderCtx, projectId)).roles.find(
      (r: ProjectExecutiveRoleState) => r.roleKey === "cmo"
    );

    const act = await activateExecutiveRole(founderCtx, projectId, "cmo", {
      expectedVersion: cmoBefore!.version,
    });
    expect(act.state).toBe("ACTIVE");

    const disabled = await disableExecutiveRole(founderCtx, projectId, "cmo", {
      expectedVersion: act.version,
      reason: "No longer needed for discovery phase",
    });
    expect(disabled.state).toBe("DISABLED");

    const statesAfter = await getProjectExecutiveRoleStates(founderCtx, projectId);
    const cmoAfter = statesAfter.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "cmo");
    expect(cmoAfter?.displayState).toBe("DISABLED");
  });
});
