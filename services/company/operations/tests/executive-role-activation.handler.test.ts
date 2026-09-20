import { describe, it, expect, beforeEach } from "vitest";
import { APIError } from "encore.dev/api";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
  createSecondWorkspace,
  makeTestTenantContext,
  createWorkspaceAgentForProfile,
  deployWorkspaceAgentForProfile,
} from "./_helpers";
import {
  listProjectExecutiveRolesApi,
  selectProjectExecutivePresetApi,
  activateProjectExecutiveRoleApi,
  disableProjectExecutiveRoleApi,
  activateWorkspaceExecutiveRoleApi,
  disableWorkspaceExecutiveRoleApi,
  getProjectExecutiveStageSuggestionApi,
  bootstrapProjectP0CoreApi,
} from "../handlers/executive-role-activation.handler";
import { deployAgentToProjectApi } from "../handlers/founder-asset-deployment.handler";
import { ProjectExecutiveRoleView } from "../services/executive-role-activation.service";

describe("Executive Role Activation Handler", () => {
  let founderToken: string;
  let memberToken: string;
  let founderUserId: string;
  let workspaceId: string;
  let projectId: string;
  let foreignProjectId: string;

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    workspaceId = ws.workspaceId;
    projectId = ws.projectId;
    founderToken = ws.bearerToken;
    founderUserId = ws.userId;

    const member = await addMemberToWorkspace(workspaceId, "member");
    memberToken = member.bearerToken;

    const secondWs = await createSecondWorkspace();
    foreignProjectId = secondWs.projectId;
  });

  it("does not disclose a foreign Project", async () => {
    await expect(
      listProjectExecutiveRolesApi({
        authorization: founderToken,
        workspaceId,
        projectId: foreignProjectId,
      })
    ).rejects.toThrow(/Project not found/);
  });

  it("does not fall back to operations for CISO", async () => {
    await expect(
      activateWorkspaceExecutiveRoleApi({
        authorization: founderToken,
        workspaceId,
        roleKey: "ciso",
        expectedVersion: 1,
      })
    ).rejects.toThrow(/EXECUTIVE_ROLE_NOT_AVAILABLE/);
  });

  it("requires founder authorization: member caller gets 403", async () => {
    await expect(
      activateWorkspaceExecutiveRoleApi({
        authorization: memberToken,
        workspaceId,
        roleKey: "cfo",
        expectedVersion: 1,
      })
    ).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED|FOUNDER_AUTHORIZATION_REQUIRED/);

    await expect(
      disableWorkspaceExecutiveRoleApi({
        authorization: memberToken,
        workspaceId,
        roleKey: "cfo",
      })
    ).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED|FOUNDER_AUTHORIZATION_REQUIRED/);
  });

  it("allows Founder to activate eligible role, handles CAS conflict, and allows disable", async () => {
    // 1. Deploy finance agent V2 vào Project → office cfo khả dụng.
    await deployWorkspaceAgentForProfile(
      makeTestTenantContext({
        workspaceId,
        userId: founderUserId,
        membershipRole: "founder",
        isAiAgent: false,
      }),
      projectId,
      "finance"
    );

    // 2. List executive roles via handler (read-model Project-scoped mới).
    const listBefore = await listProjectExecutiveRolesApi({
      authorization: founderToken,
      workspaceId,
      projectId,
    });
    const cfoBefore = listBefore.roles.find((r: ProjectExecutiveRoleView) => r.roleKey === "cfo");
    expect(cfoBefore?.officeState).toBe("AVAILABLE_NOT_ACTIVATED");
    expect(cfoBefore?.effectiveState).toBe("OFFICE_DISABLED");

    // 3. Founder activates CFO ở cấp Workspace
    const activated = await activateWorkspaceExecutiveRoleApi({
      authorization: founderToken,
      workspaceId,
      roleKey: "cfo",
      idempotencyKey: "h-act-cfo-1",
    });
    expect(activated.state).toBe("ACTIVE");
    expect(activated.roleKey).toBe("cfo");

    // 4. Stale expectedVersion throws CAS conflict
    await expect(
      activateWorkspaceExecutiveRoleApi({
        authorization: founderToken,
        workspaceId,
        roleKey: "cfo",
        expectedVersion: 999,
      })
    ).rejects.toThrow(/CAS_CONFLICT|stale/i);

    // 5. Read-model giờ EFFECTIVE (office ACTIVE + deployment ACTIVE).
    const listActive = await listProjectExecutiveRolesApi({
      authorization: founderToken,
      workspaceId,
      projectId,
    });
    const cfoActive = listActive.roles.find((r: ProjectExecutiveRoleView) => r.roleKey === "cfo");
    expect(cfoActive?.effectiveState).toBe("EFFECTIVE");

    // 6. Disable CFO ở cấp Workspace
    const disabled = await disableWorkspaceExecutiveRoleApi({
      authorization: founderToken,
      workspaceId,
      roleKey: "cfo",
      expectedVersion: activated.version,
      reason: "No longer needed",
    });
    expect(disabled.state).toBe("DISABLED");

    // 7. Project projection phản ánh OFFICE_DISABLED
    const listAfter = await listProjectExecutiveRolesApi({
      authorization: founderToken,
      workspaceId,
      projectId,
    });
    const cfoAfter = listAfter.roles.find((r: ProjectExecutiveRoleView) => r.roleKey === "cfo");
    expect(cfoAfter?.officeState).toBe("DISABLED");
    expect(cfoAfter?.effectiveState).toBe("OFFICE_DISABLED");
  });

  it("returns a stage suggestion for the project's current lifecycle stage", async () => {
    const ctx = makeTestTenantContext({
      workspaceId,
      userId: founderUserId,
      membershipRole: "founder",
      isAiAgent: false,
    });
    for (const profileKey of ["operations", "finance", "marketing", "product"]) {
      await deployWorkspaceAgentForProfile(ctx, projectId, profileKey);
    }

    const suggestion = await getProjectExecutiveStageSuggestionApi({
      authorization: founderToken,
      workspaceId,
      projectId,
    });

    expect(suggestion.stage).toBe("P0_DISCOVERY");
    expect([...suggestion.workspaceOfficeToEnable].sort()).toEqual([
      "cfo",
      "chief_of_staff",
      "cmo",
      "cpo",
    ]);
    expect(suggestion.projectAgentsToDeploy).toEqual([]);
  });

  it("lets a Founder explicitly bootstrap P0 Core for an existing P0 Project", async () => {
    const bootstrapped = await bootstrapProjectP0CoreApi({
      authorization: founderToken,
      workspaceId,
      projectId,
    });
    expect(bootstrapped.roleKeys).toEqual(["chief_of_staff", "cfo", "cmo", "cpo"]);

    const board = await listProjectExecutiveRolesApi({
      authorization: founderToken,
      workspaceId,
      projectId,
    });
    for (const roleKey of bootstrapped.roleKeys) {
      expect(board.roles.find((role) => role.roleKey === roleKey)).toMatchObject({
        officeState: "ACTIVE",
        projectDeploymentState: "ACTIVE",
        effectiveState: "EFFECTIVE",
      });
    }

    // Retry cùng lệnh không tạo thêm Workforce/Agent/deployment.
    await expect(
      bootstrapProjectP0CoreApi({ authorization: founderToken, workspaceId, projectId })
    ).resolves.toMatchObject({ projectId });
  });

  it("deploys a Workspace Agent to a Project through the public endpoint", async () => {
    const ctx = makeTestTenantContext({
      workspaceId,
      userId: founderUserId,
      membershipRole: "founder",
      isAiAgent: false,
    });
    const { workspaceAgentId } = await createWorkspaceAgentForProfile(ctx, "finance");

    const deployed = await deployAgentToProjectApi({
      authorization: founderToken,
      workspaceId,
      projectId,
      workspaceAgentId,
    });
    expect(deployed.state).toBe("ACTIVE");
    expect(deployed.workspaceAgentId).toBe(workspaceAgentId);

    // Member không được deploy (chỉ human Founder).
    await expect(
      deployAgentToProjectApi({
        authorization: memberToken,
        workspaceId,
        projectId,
        workspaceAgentId,
      })
    ).rejects.toThrow(/Missing authority|FOUNDER|permission/i);
  });

  describe("deprecated project-scoped mutation endpoints", () => {
    // Giữ endpoint nhưng fail rõ ràng (không 404 mù, không im lặng thành công)
    // để client cũ biết chính xác phải chuyển sang đâu.
    it("selectProjectExecutivePresetApi fails with a pointer to the workspace endpoint", async () => {
      await expect(
        selectProjectExecutivePresetApi({
          authorization: founderToken,
          workspaceId,
          projectId,
          presetKey: "startup-discovery",
          expectedVersion: 1,
        })
      ).rejects.toThrow(
        /deprecated.*\/operations\/workspaces\/:workspaceId\/executive-roles\/:roleKey\/activate/s
      );
    });

    it("activateProjectExecutiveRoleApi fails with a pointer to the workspace endpoint", async () => {
      await expect(
        activateProjectExecutiveRoleApi({
          authorization: founderToken,
          workspaceId,
          projectId,
          roleKey: "cfo",
        })
      ).rejects.toThrow(
        /deprecated.*\/operations\/workspaces\/:workspaceId\/executive-roles\/:roleKey\/activate/s
      );
    });

    it("disableProjectExecutiveRoleApi fails with a pointer to the workspace endpoint", async () => {
      await expect(
        disableProjectExecutiveRoleApi({
          authorization: founderToken,
          workspaceId,
          projectId,
          roleKey: "cfo",
        })
      ).rejects.toThrow(
        /deprecated.*\/operations\/workspaces\/:workspaceId\/executive-roles\/:roleKey\/disable/s
      );
    });

    it("deprecated endpoints must not mutate any state", async () => {
      const ctx = makeTestTenantContext({
        workspaceId,
        userId: founderUserId,
        membershipRole: "founder",
        isAiAgent: false,
      });
      await deployWorkspaceAgentForProfile(ctx, projectId, "finance");

      await expect(
        activateProjectExecutiveRoleApi({
          authorization: founderToken,
          workspaceId,
          projectId,
          roleKey: "cfo",
        })
      ).rejects.toThrow(/deprecated/);

      const list = await listProjectExecutiveRolesApi({
        authorization: founderToken,
        workspaceId,
        projectId,
      });
      const cfo = list.roles.find((r: ProjectExecutiveRoleView) => r.roleKey === "cfo");
      // Office chưa bật → OFFICE_DISABLED (endpoint deprecated không bật lén).
      expect(cfo?.officeState).toBe("AVAILABLE_NOT_ACTIVATED");
      expect(cfo?.effectiveState).toBe("OFFICE_DISABLED");
    });
  });
});
