import { describe, it, expect, beforeEach } from "vitest";
import { APIError } from "encore.dev/api";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
  createSecondWorkspace,
  makeTestTenantContext,
} from "./_helpers";
import { db, schema } from "../models/db";
import { and, eq } from "drizzle-orm";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  getProjectExecutiveRoleStates,
  selectStartupCorePreset,
  activateExecutiveRole,
  ProjectExecutiveRoleState,
} from "../services/executive-role-activation.service";
import {
  activateProjectStartupTeamMember,
} from "../services/project-startup-team.service";
import {
  activateWorkspaceExecutiveRole,
  disableWorkspaceExecutiveRole,
} from "../services/workspace-executive-role-activation.service";
import { createProjectService } from "../services/project.service";

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

  it("activates CCO when Customer Support is ACTIVE, and enforces CAS versioning", async () => {
    await activateProjectStartupTeamMember(founderCtx, projectId, "customer_support", { expectedVersion: 1 });
    const statesBefore = await getProjectExecutiveRoleStates(founderCtx, projectId);
    const ccoBefore = statesBefore.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "cco");
    expect(ccoBefore?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");
    const activated = await activateExecutiveRole(founderCtx, projectId, "cco", {
      expectedVersion: ccoBefore!.version,
      idempotencyKey: "act-cco-1",
    });
    expect(activated.state).toBe("ACTIVE");
  });

  it("refuses CCO when Customer Support assignment is not ACTIVE", async () => {
    const statesBefore = await getProjectExecutiveRoleStates(founderCtx, projectId);
    const ccoBefore = statesBefore.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "cco");
    await expect(
      activateExecutiveRole(founderCtx, projectId, "cco", {
        expectedVersion: ccoBefore!.version,
        idempotencyKey: "act-cco-2",
      })
    ).rejects.toThrow(/EXECUTIVE_ROLE_NOT_AVAILABLE/);
  });

  it("selectStartupCorePreset no longer drives the board — preset must not auto-activate anything", async () => {
    // 2026-09-14: activation chuyển sang cấp Workspace và chỉ xảy ra khi
    // Founder gọi tường minh. Preset (đường cũ, đã deprecate ở tầng handler)
    // KHÔNG được phép tự bật role nào trên board nữa — đây là guard chống
    // auto-activation lén quay lại (CLAUDE.md quy tắc #5).
    await activateProjectStartupTeamMember(founderCtx, projectId, "marketing", { expectedVersion: 1 });

    const result = await selectStartupCorePreset(founderCtx, projectId, {
      presetKey: "startup-discovery",
      expectedVersion: 1,
      idempotencyKey: "preset-disc-1",
    });
    expect(result.presetKey).toBe("startup-discovery");

    const states = await getProjectExecutiveRoleStates(founderCtx, projectId);
    const cmo = states.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "cmo");
    const cfo = states.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "cfo");
    const cos = states.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "chief_of_staff");

    // marketing ACTIVE → cmo khả dụng, nhưng KHÔNG được tự activate.
    expect(cmo?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");
    // finance/operations vẫn TEMPLATE ở mọi Project → gate UNAVAILABLE giữ nguyên.
    expect(cfo?.displayState).toBe("UNAVAILABLE");
    expect(cos?.displayState).toBe("UNAVAILABLE");
    // Preset cũng không còn được phản ánh trong board projection.
    expect(states.settings).toBeUndefined();
  });

  it("disabling a workspace-activated role is reflected in the project projection", async () => {
    await activateProjectStartupTeamMember(founderCtx, projectId, "marketing", { expectedVersion: 1 });
    const cmoBefore = (await getProjectExecutiveRoleStates(founderCtx, projectId)).roles.find(
      (r: ProjectExecutiveRoleState) => r.roleKey === "cmo"
    );
    expect(cmoBefore?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");

    const act = await activateWorkspaceExecutiveRole(founderCtx, "cmo", {});
    expect(act.state).toBe("ACTIVE");
    expect(
      (await getProjectExecutiveRoleStates(founderCtx, projectId)).roles.find(
        (r: ProjectExecutiveRoleState) => r.roleKey === "cmo"
      )?.displayState
    ).toBe("ACTIVE");

    const disabled = await disableWorkspaceExecutiveRole(founderCtx, "cmo", {
      expectedVersion: act.version,
      reason: "No longer needed for discovery phase",
    });
    expect(disabled.state).toBe("DISABLED");

    const statesAfter = await getProjectExecutiveRoleStates(founderCtx, projectId);
    const cmoAfter = statesAfter.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "cmo");
    expect(cmoAfter?.displayState).toBe("DISABLED");
  });

  it("proves operations lifecycle: UNAVAILABLE -> AVAILABLE_NOT_ACTIVATED (no auto-activation) -> ACTIVE with CAS", async () => {
    // 1. Before operations active, both chief_of_staff and coo are UNAVAILABLE
    const beforeStates = await getProjectExecutiveRoleStates(founderCtx, projectId);
    const cosBefore = beforeStates.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "chief_of_staff");
    const cooBefore = beforeStates.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "coo");
    expect(cosBefore?.displayState).toBe("UNAVAILABLE");
    expect(cooBefore?.displayState).toBe("UNAVAILABLE");

    // Attempting to activate coo or chief_of_staff before operations is active fails
    await expect(
      activateExecutiveRole(founderCtx, projectId, "coo", { expectedVersion: cooBefore!.version })
    ).rejects.toThrow(/EXECUTIVE_ROLE_NOT_AVAILABLE/);

    // 2. Activate ONLY operations profile in startup team
    await activateProjectStartupTeamMember(founderCtx, projectId, "operations", { expectedVersion: 1 });

    // 3. Both roles become AVAILABLE_NOT_ACTIVATED
    const midStates = await getProjectExecutiveRoleStates(founderCtx, projectId);
    const cosMid = midStates.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "chief_of_staff");
    const cooMid = midStates.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "coo");
    expect(cosMid?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");
    expect(cooMid?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");

    // Profile activation MUST NOT insert any executive role activations into the DB
    const existingActs = await db
      .select()
      .from(schema.projectExecutiveRoleActivations)
      .where(
        and(
          eq(schema.projectExecutiveRoleActivations.workspaceId, BigInt(founderCtx.workspaceId)),
          eq(schema.projectExecutiveRoleActivations.projectId, BigInt(projectId))
        )
      );
    const opsRoleActs = existingActs.filter((a) => a.roleKey === "chief_of_staff" || a.roleKey === "coo");
    expect(opsRoleActs).toHaveLength(0);

    // 4. Direct Founder activation reaches ACTIVE with CAS
    const cosAct = await activateExecutiveRole(founderCtx, projectId, "chief_of_staff", {
      expectedVersion: cosMid!.version,
      idempotencyKey: "act-cos-1",
    });
    expect(cosAct.state).toBe("ACTIVE");
    expect(cosAct.roleKey).toBe("chief_of_staff");

    const cooAct = await activateExecutiveRole(founderCtx, projectId, "coo", {
      expectedVersion: cooMid!.version,
      idempotencyKey: "act-coo-1",
    });
    expect(cooAct.state).toBe("ACTIVE");
    expect(cooAct.roleKey).toBe("coo");

    // Verify CAS conflict on stale version
    await expect(
      activateExecutiveRole(founderCtx, projectId, "coo", {
        expectedVersion: 999,
      })
    ).rejects.toThrow(/CAS_CONFLICT|stale/i);
  });

  it("workspace activation is shared across every Project in the workspace", async () => {
    // Operations and Marketing are ACTIVE; Finance remains TEMPLATE
    await activateProjectStartupTeamMember(founderCtx, projectId, "operations", { expectedVersion: 1 });
    await activateProjectStartupTeamMember(founderCtx, projectId, "marketing", { expectedVersion: 1 });

    await activateWorkspaceExecutiveRole(founderCtx, "cmo", {});
    await activateWorkspaceExecutiveRole(founderCtx, "chief_of_staff", {});
    await activateWorkspaceExecutiveRole(founderCtx, "coo", {});

    // Project thứ 2 trong cùng workspace thấy ngay cùng một bộ role ACTIVE —
    // đây chính là điểm khác biệt cốt lõi so với activation cấp Project cũ.
    const secondProject = await createProjectService(founderCtx, { title: "Shared Board Project" });

    for (const targetProjectId of [projectId, secondProject.id]) {
      const states = await getProjectExecutiveRoleStates(founderCtx, targetProjectId);
      const byKey = (k: string) =>
        states.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === k)?.displayState;

      expect(byKey("cmo")).toBe("ACTIVE");
      expect(byKey("chief_of_staff")).toBe("ACTIVE");
      expect(byKey("coo")).toBe("ACTIVE");
      // finance chưa ACTIVE ở Project nào → gate UNAVAILABLE vẫn giữ.
      expect(byKey("cfo")).toBe("UNAVAILABLE");
    }
  });
});
