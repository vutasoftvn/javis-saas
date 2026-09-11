import { describe, it, expect } from "vitest";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember, createSecondWorkspace } from "./_helpers";
import {
  listProjectStartupTeam,
  ensureProjectStartupTeam,
} from "../services/project-startup-team.service";
import { db, schema } from "../models/db";
import { eq, and } from "drizzle-orm";
import {
  STARTUP_TEAM_PROFILES,
  STARTUP_TEAM_PROFILE_KEYS,
} from "../../shared/contracts/startup-team-profiles.generated";

describe("Project Startup Team Service", () => {
  it("newly created project has exactly the 9 catalog profiles", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Alpha Startup",
      description: "Testing startup team creation",
    });

    const team = await listProjectStartupTeam({
      workspaceId: ws.workspaceId,
      projectId: project.id,
      actorId: ws.userId,
    });

    expect(team.map((m) => m.profileKey)).toEqual(STARTUP_TEAM_PROFILE_KEYS);

    const founder = team.find((m) => m.profileKey === "founder_assistant");
    expect(founder).toMatchObject({
      displayState: "CHAT_READY",
      runtimeReadiness: "READY",
    });

    const coding = team.find((m) => m.profileKey === "coding");
    expect(coding).toMatchObject({
      displayState: "TEMPLATE",
      runtimeReadiness: "DEFERRED_CODING",
      disabledReason: "DEFERRED_CODING",
    });

    const marketing = team.find((m) => m.profileKey === "marketing");
    expect(marketing).toMatchObject({
      displayState: "TEMPLATE",
      runtimeReadiness: "READY",
    });

    const crm = team.find((m) => m.profileKey === "crm");
    expect(crm).toMatchObject({
      displayState: "TEMPLATE",
      runtimeReadiness: "PENDING_CRM_FOUNDATION",
      disabledReason: "PENDING_CRM_FOUNDATION",
    });
  });

  it("re-running ensureProjectStartupTeam is idempotent and does not duplicate rows", async () => {
    const ws = await createTestWorkspaceWithMember();

    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Idempotent Project",
    });

    // Re-run ensureProjectStartupTeam
    await db.transaction(async (tx) => {
      await ensureProjectStartupTeam(tx, {
        workspaceId: ws.workspaceId,
        projectId: project.id,
        actorId: ws.userId,
      });
    });

    const rows = await db
      .select()
      .from(schema.projectAgentAssignments)
      .where(
        and(
          eq(schema.projectAgentAssignments.workspaceId, BigInt(ws.workspaceId)),
          eq(schema.projectAgentAssignments.projectId, BigInt(project.id))
        )
      );

    // 9 profiles
    expect(rows.length).toBe(STARTUP_TEAM_PROFILES.length);

    const team = await listProjectStartupTeam({
      workspaceId: ws.workspaceId,
      projectId: project.id,
      actorId: ws.userId,
    });
    expect(team.length).toBe(STARTUP_TEAM_PROFILES.length);
  });

  it("rejects project from another workspace with notFound", async () => {
    const wsA = await createTestWorkspaceWithMember();
    const wsB = await createSecondWorkspace();

    const projectA = await createProject({
      authorization: wsA.bearerToken,
      workspaceId: wsA.workspaceId,
      title: "Workspace A Project",
    });

    await expect(
      listProjectStartupTeam({
        workspaceId: wsB.workspaceId,
        projectId: projectA.id,
        actorId: wsB.workspaceId,
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });
});
