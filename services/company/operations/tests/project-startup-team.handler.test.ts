import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import { createProjectService } from "../services/project.service";
import {
  listProjectStartupTeamApi,
  activateProjectStartupTeamMemberApi,
  pauseProjectStartupTeamMemberApi,
  getProjectAgentRunAuthorityApi,
} from "../handlers/project-startup-team.handler";
import {
  AGENT_PROFILE_SPEC_HASH,
  AGENT_PROFILE_SPEC_ID,
  AGENT_PROFILE_SPEC_VERSION,
} from "../services/ai-member.service";

describe("project-startup-team handler authorization & governance", () => {
  it("rejects unauthenticated requests (missing bearer token)", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    await expect(
      listProjectStartupTeamApi({
        authorization: undefined,
        workspaceId: ws.workspaceId,
        projectId: ws.projectId,
      })
    ).rejects.toThrow(/unauthenticated|authorization|token/i);
  });

  it("returns indistinguishable 404 for project belonging to another workspace", async () => {
    const wsA = await createTestWorkspaceWithMember({ role: "founder" });
    const wsB = await createTestWorkspaceWithMember({ role: "founder" });

    // List: wsA requesting wsB's project -> 404
    await expect(
      listProjectStartupTeamApi({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        projectId: wsB.projectId,
      })
    ).rejects.toThrow(/not found/i);

    // Activate: wsA requesting wsB's project -> 404
    await expect(
      activateProjectStartupTeamMemberApi({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        projectId: wsB.projectId,
        profileKey: "marketing",
        expectedVersion: 1,
      })
    ).rejects.toThrow(/not found/i);

    // Pause: wsA requesting wsB's project -> 404
    await expect(
      pauseProjectStartupTeamMemberApi({
        authorization: wsA.bearerToken,
        workspaceId: wsA.workspaceId,
        projectId: wsB.projectId,
        profileKey: "marketing",
        expectedVersion: 1,
      })
    ).rejects.toThrow(/not found/i);
  });

  it("rejects non-founder/admin members with 403 permissionDenied for activate and pause", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    const project = await createProjectService(
      {
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: [],
        correlationId: "test",
      } as any,
      { title: "Team Project" }
    );

    // Member can list
    const listRes = await listProjectStartupTeamApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
    });
    expect(listRes.items).toHaveLength(16);

    // Member cannot activate
    await expect(
      activateProjectStartupTeamMemberApi({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        projectId: project.id,
        profileKey: "marketing",
        expectedVersion: 1,
      })
    ).rejects.toThrow(/founder or admin authority required/i);

    // Member cannot pause
    await expect(
      pauseProjectStartupTeamMemberApi({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        projectId: project.id,
        profileKey: "marketing",
        expectedVersion: 1,
      })
    ).rejects.toThrow(/founder or admin authority required/i);
  });

  it("blocks activation of founder_assistant and unready profiles", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const project = await createProjectService(
      {
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: [],
        correlationId: "test",
      } as any,
      { title: "Validation Project" }
    );

    // founder_assistant cannot be activated
    await expect(
      activateProjectStartupTeamMemberApi({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        projectId: project.id,
        profileKey: "founder_assistant",
        expectedVersion: 1,
      })
    ).rejects.toThrow(/chat co-founder/i);

    // crm is pending
    await expect(
      activateProjectStartupTeamMemberApi({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        projectId: project.id,
        profileKey: "crm",
        expectedVersion: 1,
      })
    ).rejects.toThrow(/PENDING_CRM_FOUNDATION/i);
  });

  it("allows founder/admin to activate a ready template, pins spec hash, handles optimistic concurrency & idempotency", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const project = await createProjectService(
      {
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: [],
        correlationId: "test",
      } as any,
      { title: "Execution Project" }
    );

    // 1. Activate marketing with idempotency key
    const activated = await activateProjectStartupTeamMemberApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      profileKey: "marketing",
      expectedVersion: 1,
      idempotencyKey: "act-marketing-1",
    });

    expect(activated.displayState).toBe("ACTIVE");
    expect(activated.assignmentVersion).toBe(2);
    expect(activated.activatedAt).toBeDefined();

    // 2. Repeating idempotency key returns the same view without re-incrementing version
    const repeated = await activateProjectStartupTeamMemberApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      profileKey: "marketing",
      expectedVersion: 1, // Même stale version succeeds because idempotency key matched
      idempotencyKey: "act-marketing-1",
    });
    expect(repeated.assignmentVersion).toBe(2);

    // 3. Stale version without matching idempotency key triggers 409 conflict
    await expect(
      activateProjectStartupTeamMemberApi({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        projectId: project.id,
        profileKey: "marketing",
        expectedVersion: 1,
        idempotencyKey: "new-attempt",
      })
    ).rejects.toThrow(/version conflict/i);

    // 4. Pause of ACTIVE member increments version to 3
    const paused = await pauseProjectStartupTeamMemberApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      profileKey: "marketing",
      expectedVersion: 2,
      reason: "Budget reallocated",
      idempotencyKey: "pause-marketing-1",
    });
    expect(paused.displayState).toBe("PAUSED");
    expect(paused.assignmentVersion).toBe(3);
    expect(paused.disabledReason).toBe("Budget reallocated");

    // 5. Repeating pause idempotency key returns same state
    const repeatedPause = await pauseProjectStartupTeamMemberApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      profileKey: "marketing",
      expectedVersion: 2,
      idempotencyKey: "pause-marketing-1",
    });
    expect(repeatedPause.assignmentVersion).toBe(3);
  });

  it("handles internal run-authority read with worker service authentication", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const project = await createProjectService(
      {
        workspaceId: ws.workspaceId,
        userId: ws.userId,
        membershipRole: "founder",
        permissions: [],
        correlationId: "test",
      } as any,
      { title: "Authority Project" }
    );

    // 1. Missing service token -> 401
    await expect(
      getProjectAgentRunAuthorityApi({
        serviceToken: undefined,
        workspaceId: ws.workspaceId,
        projectId: project.id,
        profileKey: "operations",
      })
    ).rejects.toThrow(/missing service token/i);

    // 2. Unassigned / TEMPLATE state -> 404
    await expect(
      getProjectAgentRunAuthorityApi({
        serviceToken: "dev-worker-service-token",
        workspaceId: ws.workspaceId,
        projectId: project.id,
        profileKey: "finance",
      })
    ).rejects.toThrow(/not actively assigned/i);

    // 3. Activate finance
    await activateProjectStartupTeamMemberApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      profileKey: "finance",
      expectedVersion: 1,
    });

    // 4. ACTIVE -> 200 with full authority
    const auth = await getProjectAgentRunAuthorityApi({
      serviceToken: "dev-worker-service-token",
      workspaceId: ws.workspaceId,
      projectId: project.id,
      profileKey: "finance",
    });

    expect(auth.projectId).toBe(project.id);
    expect(auth.workspaceId).toBe(ws.workspaceId);
    expect(auth.profileKey).toBe("finance");
    expect(auth.assignmentVersion).toBe(2);
    expect(auth.agentWorkforceMemberId).toBeDefined();
    expect(auth.spec.id).toBe("cosa.agents.finance");
    expect(auth.spec.version).toBe("1.1.0");
    expect(auth.spec.hash).toBe(
      "21bacc10efd681f204e62e827111853a468436fa2413857bdc1b1e7e0c38be96"
    );

    // 5. Pause finance -> run-authority returns 404
    await pauseProjectStartupTeamMemberApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      profileKey: "finance",
      expectedVersion: 2,
    });

    const workerToken =
      process.env.COSA_WORKER_SERVICE_TOKEN ?? "dev-worker-service-token";

    await expect(
      getProjectAgentRunAuthorityApi({
        serviceToken: workerToken,
        workspaceId: ws.workspaceId,
        projectId: project.id,
        profileKey: "finance",
      })
    ).rejects.toThrow(/not actively assigned/i);

    // 6. Operations activation and run-authority with pinned spec hash
    const opsAct = await activateProjectStartupTeamMemberApi({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      profileKey: "operations",
      expectedVersion: 1,
    });
    expect(opsAct.displayState).toBe("ACTIVE");
    expect(opsAct.assignmentVersion).toBe(2);

    const opsAuth = await getProjectAgentRunAuthorityApi({
      serviceToken: workerToken,
      workspaceId: ws.workspaceId,
      projectId: project.id,
      profileKey: "operations",
    });

    expect(opsAuth.projectId).toBe(project.id);
    expect(opsAuth.workspaceId).toBe(ws.workspaceId);
    expect(opsAuth.profileKey).toBe("operations");
    expect(opsAuth.assignmentVersion).toBe(2);
    expect(opsAuth.agentWorkforceMemberId).toBeDefined();
    expect(opsAuth.spec.id).toBe(AGENT_PROFILE_SPEC_ID.operations);
    expect(opsAuth.spec.version).toBe(AGENT_PROFILE_SPEC_VERSION.operations);
    expect(opsAuth.spec.hash).toBe(AGENT_PROFILE_SPEC_HASH.operations);
  });
});
