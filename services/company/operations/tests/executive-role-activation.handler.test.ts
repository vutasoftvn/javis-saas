import { describe, it, expect, beforeEach } from "vitest";
import { APIError } from "encore.dev/api";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
  createSecondWorkspace,
  makeTestTenantContext,
} from "./_helpers";
import {
  listProjectExecutiveRolesApi,
  selectProjectExecutivePresetApi,
  activateProjectExecutiveRoleApi,
  disableProjectExecutiveRoleApi,
  activateWorkspaceExecutiveRoleApi,
  disableWorkspaceExecutiveRoleApi,
  getProjectExecutiveStageSuggestionApi,
} from "../handlers/executive-role-activation.handler";
import { activateProjectStartupTeamMember } from "../services/project-startup-team.service";
import { ProjectExecutiveRoleState } from "../services/executive-role-activation.service";

describe("Executive Role Activation Handler", () => {
  let founderToken: string;
  let memberToken: string;
  let workspaceId: string;
  let projectId: string;
  let foreignProjectId: string;

  beforeEach(async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    workspaceId = ws.workspaceId;
    projectId = ws.projectId;
    founderToken = ws.bearerToken;

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
    // 1. Activate finance profile in startup team
    await activateProjectStartupTeamMember(
      makeTestTenantContext({
        workspaceId,
        userId: "test-user",
        membershipRole: "founder",
        isAiAgent: false,
      }),
      projectId,
      "finance",
      { expectedVersion: 1 }
    );

    // 2. List executive roles via handler (projection theo Project vẫn dùng được)
    const listBefore = await listProjectExecutiveRolesApi({
      authorization: founderToken,
      workspaceId,
      projectId,
    });
    const cfoBefore = listBefore.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "cfo");
    expect(cfoBefore?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");

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

    // 5. Disable CFO ở cấp Workspace
    const disabled = await disableWorkspaceExecutiveRoleApi({
      authorization: founderToken,
      workspaceId,
      roleKey: "cfo",
      expectedVersion: activated.version,
      reason: "No longer needed",
    });
    expect(disabled.state).toBe("DISABLED");

    // 6. Project projection phản ánh DISABLED
    const listAfter = await listProjectExecutiveRolesApi({
      authorization: founderToken,
      workspaceId,
      projectId,
    });
    const cfoAfter = listAfter.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "cfo");
    expect(cfoAfter?.displayState).toBe("DISABLED");
  });

  it("returns a stage suggestion for the project's current lifecycle stage", async () => {
    const ctx = makeTestTenantContext({
      workspaceId,
      userId: "test-user",
      membershipRole: "founder",
      isAiAgent: false,
    });
    for (const profileKey of ["operations", "finance", "marketing", "product"]) {
      await activateProjectStartupTeamMember(ctx, projectId, profileKey, { expectedVersion: 1 });
    }

    const suggestion = await getProjectExecutiveStageSuggestionApi({
      authorization: founderToken,
      workspaceId,
      projectId,
    });

    expect(suggestion.stage).toBe("P0_DISCOVERY");
    expect([...suggestion.toActivate].sort()).toEqual(["cfo", "chief_of_staff", "cmo", "cpo"]);
    expect(suggestion.toSuggestDeactivate).toEqual([]);
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
        userId: "test-user",
        membershipRole: "founder",
        isAiAgent: false,
      });
      await activateProjectStartupTeamMember(ctx, projectId, "finance", { expectedVersion: 1 });

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
      const cfo = list.roles.find((r: ProjectExecutiveRoleState) => r.roleKey === "cfo");
      expect(cfo?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");
    });
  });
});
