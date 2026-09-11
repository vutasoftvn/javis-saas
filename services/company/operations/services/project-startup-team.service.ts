import { APIError } from "encore.dev/api";
import { and, eq, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  STARTUP_TEAM_PROFILES,
  STARTUP_TEAM_PROFILE_KEYS,
  StartupTeamProfileKey,
  ProjectStartupTeamMember,
} from "../../shared/contracts/startup-team-profiles.generated";

export type DbTx = Parameters<Parameters<typeof db.transaction>[0]>[0];

const { projects, projectAgentAssignments, projectAgentAssignmentEvents } = schema;

/**
 * Đảm bảo Project có đầy đủ 9 catalog template assignments (idempotent).
 * Dùng trong transaction tạo Project hoặc khi repair/backfill.
 */
export async function ensureProjectStartupTeam(
  tx: DbTx,
  input: {
    workspaceId: string;
    projectId: string;
    actorId: string;
  }
): Promise<void> {
  const wsId = BigInt(input.workspaceId);
  const projId = BigInt(input.projectId);
  const actorId = BigInt(input.actorId);

  // Tìm các profileKey đã tồn tại
  const existingRows = await tx
    .select({ profileKey: projectAgentAssignments.profileKey })
    .from(projectAgentAssignments)
    .where(
      and(
        eq(projectAgentAssignments.workspaceId, wsId),
        eq(projectAgentAssignments.projectId, projId)
      )
    );

  const existingKeys = new Set(existingRows.map((r) => r.profileKey));

  for (const profile of STARTUP_TEAM_PROFILES) {
    if (existingKeys.has(profile.key)) {
      continue;
    }

    const assignmentId = generateSnowflake();
    const eventId = generateSnowflake();
    const disabledReason =
      profile.runtimeReadiness !== "READY" ? profile.runtimeReadiness : null;

    await tx.insert(projectAgentAssignments).values({
      id: assignmentId,
      workspaceId: wsId,
      projectId: projId,
      profileKey: profile.key,
      state: "TEMPLATE",
      disabledReason,
      version: 1,
      createdBy: actorId,
    });

    await tx.insert(projectAgentAssignmentEvents).values({
      id: eventId,
      workspaceId: wsId,
      projectId: projId,
      assignmentId,
      eventType: "ASSIGNMENT_TEMPLATE_CREATED",
      fromState: null,
      toState: "TEMPLATE",
      assignmentVersion: 1,
      actorId,
      eventPayload: { profileKey: profile.key },
    });
  }
}

/**
 * Lấy danh sách Startup Team của Project.
 * Trả về đủ 9 profile theo catalog chuẩn.
 */
export async function listProjectStartupTeam(input: {
  workspaceId: string;
  projectId: string;
  actorId?: string;
}): Promise<ProjectStartupTeamMember[]> {
  const wsId = BigInt(input.workspaceId);
  const projId = BigInt(input.projectId);

  // Kiểm tra Project có tồn tại và thuộc Workspace không
  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!project) {
    throw APIError.notFound("Project not found");
  }

  // Lấy các assignment rows hiện có
  const rows = await db
    .select()
    .from(projectAgentAssignments)
    .where(
      and(
        eq(projectAgentAssignments.workspaceId, wsId),
        eq(projectAgentAssignments.projectId, projId)
      )
    );

  const rowMap = new Map<string, (typeof rows)[number]>();
  for (const r of rows) {
    rowMap.set(r.profileKey, r);
  }

  return STARTUP_TEAM_PROFILES.map((profile): ProjectStartupTeamMember => {
    if (profile.key === "founder_assistant") {
      return {
        profileKey: "founder_assistant",
        label: profile.label,
        displayState: "CHAT_READY",
        runtimeReadiness: "READY",
      };
    }

    const row = rowMap.get(profile.key);
    if (!row) {
      return {
        profileKey: profile.key,
        label: profile.label,
        displayState: "TEMPLATE",
        runtimeReadiness: profile.runtimeReadiness,
        disabledReason:
          profile.runtimeReadiness !== "READY"
            ? profile.runtimeReadiness
            : undefined,
      };
    }

    return {
      profileKey: profile.key,
      label: profile.label,
      displayState: row.state,
      runtimeReadiness: profile.runtimeReadiness,
      disabledReason:
        row.disabledReason ??
        (profile.runtimeReadiness !== "READY"
          ? profile.runtimeReadiness
          : undefined),
      assignmentVersion: row.version,
      activatedAt: row.activatedAt ? row.activatedAt.toISOString() : undefined,
      activatedBy: row.activatedBy ? row.activatedBy.toString() : undefined,
    };
  });
}
