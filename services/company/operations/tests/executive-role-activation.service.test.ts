import { describe, it, expect, beforeEach } from "vitest";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
  createSecondWorkspace,
  makeTestTenantContext,
  deployWorkspaceAgentForProfile,
} from "./_helpers";
import { db, schema } from "../models/db";
import { and, eq } from "drizzle-orm";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  getProjectExecutiveRoleStates,
  ProjectExecutiveRoleView,
} from "../services/executive-role-activation.service";
import {
  activateWorkspaceExecutiveRole,
  disableWorkspaceExecutiveRole,
} from "../services/workspace-executive-role-activation.service";
import { createProjectService } from "../services/project.service";

function roleOf(
  roles: ProjectExecutiveRoleView[],
  roleKey: string
): ProjectExecutiveRoleView | undefined {
  return roles.find((r) => r.roleKey === roleKey);
}

describe("Executive Role Activation Service (Project-scoped read model)", () => {
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

  it("lists all 13 roles with the new effective-state shape", async () => {
    const states = await getProjectExecutiveRoleStates(founderCtx, projectId);
    expect(states.projectId).toBe(projectId);
    expect(states.roles).toHaveLength(15);

    const cfo = roleOf(states.roles, "cfo");
    expect(cfo).toBeDefined();
    // Chưa bật office → officeState UNAVAILABLE, không thể EFFECTIVE.
    expect(cfo?.officeState).toBe("UNAVAILABLE");
    expect(cfo?.effectiveState).toBe("OFFICE_DISABLED");
    expect(cfo?.stageEligibility).toBe("ALLOWED"); // cfo là persistent role
    expect(cfo?.workspaceOfficeVersion).toBe(1);
  });

  it("automatically makes the four P0 Core roles effective for a new Founder project", async () => {
    const project = await createProjectService(founderCtx, {
      title: "New P0 Core project",
      creationMode: "NEW",
    });

    const board = await getProjectExecutiveRoleStates(founderCtx, project.id);
    for (const roleKey of ["chief_of_staff", "cfo", "cmo", "cpo"]) {
      const role = roleOf(board.roles, roleKey);
      expect(role).toMatchObject({
        officeState: "ACTIVE",
        projectDeploymentState: "ACTIVE",
        effectiveState: "EFFECTIVE",
      });
      expect(role?.workspaceAgentId).toBeDefined();
      expect(role?.projectAgentDeploymentId).toBeDefined();
    }

    // Không mở rộng ngầm quyền lực sang các Office ngoài P0 Core.
    expect(roleOf(board.roles, "coo")?.effectiveState).toBe("OFFICE_DISABLED");
    expect(roleOf(board.roles, "coo")?.officeState).not.toBe("ACTIVE");
    expect(roleOf(board.roles, "ciso")?.officeState).toBe("UNAVAILABLE");
  });

  it("does not disclose a foreign Project", async () => {
    await expect(
      getProjectExecutiveRoleStates(founderCtx, foreignProjectId)
    ).rejects.toThrow(/Project not found/);
  });

  it("permits only a human Founder to activate a Workspace office role", async () => {
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "finance");

    await expect(
      activateWorkspaceExecutiveRole(memberCtx, "cfo", { expectedVersion: 1 })
    ).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED|FOUNDER_AUTHORIZATION_REQUIRED/);

    await expect(
      activateWorkspaceExecutiveRole(aiCtx, "cfo", { expectedVersion: 1 })
    ).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED|FOUNDER_AUTHORIZATION_REQUIRED/);
  });

  it("reports office ACTIVE but DEPLOYMENT_INACTIVE until the Workspace Agent is deployed to the Project", async () => {
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "finance");
    await activateWorkspaceExecutiveRole(founderCtx, "cfo", {});

    const states = await getProjectExecutiveRoleStates(founderCtx, projectId);
    const cfo = roleOf(states.roles, "cfo");
    expect(cfo?.officeState).toBe("ACTIVE");
    expect(cfo?.projectDeploymentState).toBe("ACTIVE");
    expect(cfo?.effectiveState).toBe("EFFECTIVE");
    expect(cfo?.projectAgentDeploymentId).toBeDefined();
  });

  it("deploying only to Project A keeps an onboarded P0 Project B at DEPLOYMENT_INACTIVE (no cross-Project leak)", async () => {
    // Workspace office ACTIVE + Agent chỉ deploy vào Project A (projectId).
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "finance");
    await activateWorkspaceExecutiveRole(founderCtx, "cfo", {});

    const projectB = await createProjectService(founderCtx, {
      title: "Project B",
      creationMode: "ONBOARD_EXISTING",
      initialLifecycleStage: "P0_DISCOVERY",
      initializationRationale: "Test Project B deliberately has no P0 Core bootstrap",
    });

    const statesA = await getProjectExecutiveRoleStates(founderCtx, projectId);
    const cfoA = roleOf(statesA.roles, "cfo");
    expect(cfoA?.officeState).toBe("ACTIVE");
    expect(cfoA?.projectDeploymentState).toBe("ACTIVE");
    expect(cfoA?.effectiveState).toBe("EFFECTIVE");

    const statesB = await getProjectExecutiveRoleStates(founderCtx, projectB.id);
    const cfoB = roleOf(statesB.roles, "cfo");
    expect(cfoB?.officeState).toBe("ACTIVE"); // office dùng chung Workspace
    expect(cfoB?.projectDeploymentState).toBe("INACTIVE");
    expect(cfoB?.effectiveState).toBe("DEPLOYMENT_INACTIVE");
    expect(cfoB?.projectAgentDeploymentId).toBeUndefined();
  });

  it("reports STAGE_FORBIDDEN for a non-persistent role at a disallowed stage", async () => {
    // cco (customer_support) chỉ được gợi ý từ P4; Project mặc định ở P0_DISCOVERY.
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "customer_support");
    await activateWorkspaceExecutiveRole(founderCtx, "cco", {});

    const states = await getProjectExecutiveRoleStates(founderCtx, projectId);
    const cco = roleOf(states.roles, "cco");
    expect(cco?.officeState).toBe("ACTIVE");
    expect(cco?.projectDeploymentState).toBe("ACTIVE");
    expect(cco?.stageEligibility).toBe("NOT_SUGGESTED");
    expect(cco?.effectiveState).toBe("STAGE_FORBIDDEN");
  });

  it("disabling the Workspace office flips the Project projection to OFFICE_DISABLED", async () => {
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "marketing");
    const act = await activateWorkspaceExecutiveRole(founderCtx, "cmo", {});

    const before = roleOf(
      (await getProjectExecutiveRoleStates(founderCtx, projectId)).roles,
      "cmo"
    );
    expect(before?.effectiveState).toBe("EFFECTIVE");

    await disableWorkspaceExecutiveRole(founderCtx, "cmo", {
      expectedVersion: act.version,
      reason: "No longer needed for discovery",
    });

    const after = roleOf(
      (await getProjectExecutiveRoleStates(founderCtx, projectId)).roles,
      "cmo"
    );
    expect(after?.officeState).toBe("DISABLED");
    expect(after?.effectiveState).toBe("OFFICE_DISABLED");
  });

  it("never reads or writes the deprecated project_executive_role_activations table", async () => {
    // Bảo vệ quyết định kiến trúc: read model mới phải KHÔNG phụ thuộc bảng
    // role-activation cấp Project cũ (bảng đó giữ lại chỉ vì migration expand).
    await deployWorkspaceAgentForProfile(founderCtx, projectId, "finance");
    await activateWorkspaceExecutiveRole(founderCtx, "cfo", {});

    await getProjectExecutiveRoleStates(founderCtx, projectId);

    const legacyRows = await db
      .select()
      .from(schema.projectExecutiveRoleActivations)
      .where(
        and(
          eq(schema.projectExecutiveRoleActivations.workspaceId, BigInt(founderCtx.workspaceId)),
          eq(schema.projectExecutiveRoleActivations.projectId, BigInt(projectId))
        )
      );
    expect(legacyRows).toHaveLength(0);
  });
});
