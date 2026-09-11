import { describe, it, expect, beforeEach } from "vitest";
import { APIError } from "encore.dev/api";
import {
  createTestWorkspaceWithMember,
  addMemberToWorkspace,
  createSecondWorkspace,
} from "./_helpers";
import {
  listProjectExecutiveRolesApi,
  selectProjectExecutivePresetApi,
  activateProjectExecutiveRoleApi,
  disableProjectExecutiveRoleApi,
} from "../handlers/executive-role-activation.handler";
import { activateProjectStartupTeamMember } from "../services/project-startup-team.service";

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
      activateProjectExecutiveRoleApi({
        authorization: founderToken,
        workspaceId,
        projectId,
        roleKey: "ciso",
        expectedVersion: 1,
      })
    ).rejects.toThrow(/EXECUTIVE_ROLE_NOT_AVAILABLE/);
  });

  it("requires founder authorization: member caller gets 403", async () => {
    await expect(
      activateProjectExecutiveRoleApi({
        authorization: memberToken,
        workspaceId,
        projectId,
        roleKey: "cfo",
        expectedVersion: 1,
      })
    ).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED|FOUNDER_AUTHORIZATION_REQUIRED/);

    await expect(
      selectProjectExecutivePresetApi({
        authorization: memberToken,
        workspaceId,
        projectId,
        presetKey: "startup-discovery",
      })
    ).rejects.toThrow(/FOUNDER_AUTHORITY_REQUIRED|FOUNDER_AUTHORIZATION_REQUIRED/);
  });

  it("allows Founder to activate eligible role, handles CAS conflict, and allows disable", async () => {
    // 1. Activate finance profile in startup team
    await activateProjectStartupTeamMember(
      {
        workspaceId,
        userId: "test-user",
        membershipRole: "founder",
        isAiAgent: false,
      },
      projectId,
      "finance",
      { expectedVersion: 1 }
    );

    // 2. List executive roles via handler
    const listBefore = await listProjectExecutiveRolesApi({
      authorization: founderToken,
      workspaceId,
      projectId,
    });
    const cfoBefore = listBefore.roles.find((r) => r.roleKey === "cfo");
    expect(cfoBefore?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");

    // 3. Founder activates CFO via handler
    const activated = await activateProjectExecutiveRoleApi({
      authorization: founderToken,
      workspaceId,
      projectId,
      roleKey: "cfo",
      expectedVersion: cfoBefore!.version,
      idempotencyKey: "h-act-cfo-1",
    });
    expect(activated.state).toBe("ACTIVE");
    expect(activated.roleKey).toBe("cfo");

    // 4. Stale expectedVersion throws CAS conflict
    await expect(
      activateProjectExecutiveRoleApi({
        authorization: founderToken,
        workspaceId,
        projectId,
        roleKey: "cfo",
        expectedVersion: 999,
      })
    ).rejects.toThrow(/CAS_CONFLICT|stale/i);

    // 5. Disable CFO via handler
    const disabled = await disableProjectExecutiveRoleApi({
      authorization: founderToken,
      workspaceId,
      projectId,
      roleKey: "cfo",
      expectedVersion: activated.version,
      reason: "No longer needed",
    });
    expect(disabled.state).toBe("DISABLED");

    // 6. List returns DISABLED displayState
    const listAfter = await listProjectExecutiveRolesApi({
      authorization: founderToken,
      workspaceId,
      projectId,
    });
    const cfoAfter = listAfter.roles.find((r) => r.roleKey === "cfo");
    expect(cfoAfter?.displayState).toBe("DISABLED");
  });

  it("allows Founder to select preset via handler", async () => {
    await activateProjectStartupTeamMember(
      {
        workspaceId,
        userId: "test-user",
        membershipRole: "founder",
        isAiAgent: false,
      },
      projectId,
      "marketing",
      { expectedVersion: 1 }
    );

    const presetRes = await selectProjectExecutivePresetApi({
      authorization: founderToken,
      workspaceId,
      projectId,
      presetKey: "startup-discovery",
      expectedVersion: 1,
    });
    expect(presetRes.presetKey).toBe("startup-discovery");

    const listRes = await listProjectExecutiveRolesApi({
      authorization: founderToken,
      workspaceId,
      projectId,
    });
    const cmo = listRes.roles.find((r) => r.roleKey === "cmo");
    expect(cmo?.displayState).toBe("ACTIVE");
  });
});
