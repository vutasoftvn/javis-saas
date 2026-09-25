import { randomUUID } from "node:crypto";
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { isLifecyclePrivileged } from "../strategy/services/lifecycle-authorization.service";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
import {
  OPERATIONS_PROJECT_AGENT_ASSIGNMENT_ACTIVATED_V1,
  OPERATIONS_PROJECT_AGENT_ASSIGNMENT_PAUSED_V1,
} from "../../shared/events/event-types";
import {
  ensureAiWorkforceMember,
  AGENT_PROFILE_SPEC_ID,
  AGENT_PROFILE_SPEC_VERSION,
  AGENT_PROFILE_SPEC_HASH,
  OwnerAgentProfile,
} from "./ai-member.service";
import {
  STARTUP_TEAM_PROFILES,
  STARTUP_TEAM_PROFILE_KEYS,
  StartupTeamProfileKey,
  ProjectStartupTeamMember,
  isStartupTeamProfileKey,
} from "../../shared/contracts/startup-team-profiles.generated";

export type DbTx = Parameters<Parameters<typeof db.transaction>[0]>[0];

const {
  projects,
  projectAgentAssignments,
  projectAgentAssignmentEvents,
  workspaceAgents,
  founderAssetEvents,
} = schema;

/**
 * Guard quyền Founder/Admin cho việc quản trị Project Startup Team.
 * Phải xác thực Project tồn tại trong đúng Workspace (tránh cross-tenant enumeration).
 */
export async function requireStartupTeamAuthority(
  ctx: TenantContext,
  projectId: string
): Promise<void> {
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!project) {
    throw APIError.notFound("Project not found");
  }

  if (!isLifecyclePrivileged(ctx.membershipRole)) {
    throw APIError.permissionDenied(
      "Founder or admin authority required to govern project startup team"
    );
  }
}

/**
 * Đảm bảo Project có đầy đủ catalog hiện hành template assignments (idempotent).
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
 * Trả về đủ profile theo catalog hiện hành.
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

export interface ActivateProjectStartupTeamMemberInput {
  expectedVersion: number;
  idempotencyKey?: string;
}

/**
 * Kích hoạt agent member cho Project (Founder/Admin governed).
 */
export async function activateProjectStartupTeamMember(
  ctx: TenantContext,
  projectId: string,
  profileKey: string,
  input: ActivateProjectStartupTeamMemberInput
): Promise<ProjectStartupTeamMember> {
  await requireStartupTeamAuthority(ctx, projectId);

  if (profileKey === "founder_assistant") {
    throw APIError.invalidArgument(
      "founder_assistant is always available as chat co-founder and cannot be activated as an operating agent"
    );
  }

  if (!isStartupTeamProfileKey(profileKey)) {
    throw APIError.notFound(`Unknown profile key '${profileKey}'`);
  }

  const profileDef = STARTUP_TEAM_PROFILES.find((p) => p.key === profileKey);
  if (!profileDef) {
    throw APIError.notFound(`Profile '${profileKey}' not found in catalog`);
  }

  if (profileDef.runtimeReadiness !== "READY") {
    throw APIError.failedPrecondition(
      `Cannot activate agent profile '${profileKey}': readiness is '${profileDef.runtimeReadiness}'`
    );
  }

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);
  const actorId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : BigInt(0);

  return await db.transaction(async (tx) => {
    let [row] = await tx
      .select()
      .from(projectAgentAssignments)
      .where(
        and(
          eq(projectAgentAssignments.workspaceId, wsId),
          eq(projectAgentAssignments.projectId, projId),
          eq(projectAgentAssignments.profileKey, profileKey)
        )
      )
      .for("update")
      .limit(1);

    if (!row) {
      await ensureProjectStartupTeam(tx, {
        workspaceId: ctx.workspaceId,
        projectId,
        actorId: ctx.workforceMemberId ?? "0",
      });
      [row] = await tx
        .select()
        .from(projectAgentAssignments)
        .where(
          and(
            eq(projectAgentAssignments.workspaceId, wsId),
            eq(projectAgentAssignments.projectId, projId),
            eq(projectAgentAssignments.profileKey, profileKey)
          )
        )
        .for("update")
        .limit(1);
    }

    if (!row) {
      throw APIError.notFound(`Assignment for '${profileKey}' not found`);
    }

    // Idempotency check: lặp lại idempotencyKey trả về trạng thái hiện tại
    if (input.idempotencyKey) {
      const existingEvents = await tx
        .select()
        .from(projectAgentAssignmentEvents)
        .where(
          and(
            eq(projectAgentAssignmentEvents.workspaceId, wsId),
            eq(projectAgentAssignmentEvents.projectId, projId),
            eq(projectAgentAssignmentEvents.assignmentId, row.id),
            eq(projectAgentAssignmentEvents.eventType, "ASSIGNMENT_ACTIVATED")
          )
        );
      const match = existingEvents.find(
        (e) => (e.eventPayload as any)?.idempotencyKey === input.idempotencyKey
      );
      if (match) {
        return {
          profileKey: profileDef.key,
          label: profileDef.label,
          displayState: row.state,
          runtimeReadiness: profileDef.runtimeReadiness,
          disabledReason: row.disabledReason ?? undefined,
          assignmentVersion: row.version,
          activatedAt: row.activatedAt ? row.activatedAt.toISOString() : undefined,
          activatedBy: row.activatedBy ? row.activatedBy.toString() : undefined,
        };
      }
    }

    // Optimistic concurrency check
    if (row.version !== input.expectedVersion) {
      throw APIError.aborted(
        `Version conflict: expected version ${input.expectedVersion}, current version is ${row.version}`
      );
    }

    // Ensure AI workforce member exists
    const workforceMemberId = await ensureAiWorkforceMember(
      tx,
      ctx.workspaceId,
      profileKey as OwnerAgentProfile
    );

    const specId = AGENT_PROFILE_SPEC_ID[profileKey as OwnerAgentProfile];
    const specVersion = AGENT_PROFILE_SPEC_VERSION[profileKey as OwnerAgentProfile];
    const specHash = AGENT_PROFILE_SPEC_HASH[profileKey as OwnerAgentProfile];
    const nextVersion = row.version + 1;
    const now = new Date();
    const policySnapshot = {
      profileKey,
      policyVersion: "1.0.0",
      activatedAt: now.toISOString(),
      readiness: profileDef.runtimeReadiness,
    };

    // Một profile nền đã được Founder kích hoạt cần có Workspace Agent V2
    // tương ứng để Founder có thể deploy nó vào chính Project ở bước tiếp
    // theo. Giữ cùng transaction với assignment để không tạo nửa trạng thái.
    const [workspaceAgent] = await tx
      .select({ id: workspaceAgents.id })
      .from(workspaceAgents)
      .where(
        and(
          eq(workspaceAgents.workspaceId, wsId),
          eq(workspaceAgents.agentAssetId, specId)
        )
      )
      .limit(1);
    if (!workspaceAgent) {
      const workspaceAgentId = generateSnowflake();
      await tx.insert(workspaceAgents).values({
        id: workspaceAgentId,
        workspaceId: wsId,
        agentAssetId: specId,
        agentAssetVersion: specVersion,
        agentDefinitionHash: specHash,
        workforceMemberId: BigInt(workforceMemberId),
        state: "ACTIVE",
        originKind: "STARTUP_TEAM",
        createdBy: actorId,
        version: 1,
      });
      await tx.insert(founderAssetEvents).values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: projId,
        actorId,
        command: "createWorkspaceAgent",
        targetKind: "AGENT",
        targetRef: { workspaceAgentId: workspaceAgentId.toString(), agentAssetId: specId },
        afterHash: specHash,
        reason: "Activate startup-team agent",
        correlationId: ctx.correlationId || randomUUID(),
        metadata: { source: "STARTUP_TEAM_ACTIVATION", profileKey },
      });
    }

    await tx
      .update(projectAgentAssignments)
      .set({
        state: "ACTIVE",
        agentWorkforceMemberId: BigInt(workforceMemberId),
        specId,
        specVersion,
        specHash,
        activationPolicySnapshot: policySnapshot,
        version: nextVersion,
        activatedAt: now,
        activatedBy: actorId,
        disabledReason: null,
        updatedAt: now,
      })
      .where(eq(projectAgentAssignments.id, row.id));

    await tx.insert(projectAgentAssignmentEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: projId,
      assignmentId: row.id,
      eventType: "ASSIGNMENT_ACTIVATED",
      fromState: row.state,
      toState: "ACTIVE",
      assignmentVersion: nextVersion,
      actorId,
      occurredAt: now,
      eventPayload: {
        profileKey,
        specId,
        specVersion,
        specHash,
        idempotencyKey: input.idempotencyKey ?? null,
        label: `${profileDef.label} activated`,
      },
    });

    const envelope = makeBusinessEvent({
      eventType: OPERATIONS_PROJECT_AGENT_ASSIGNMENT_ACTIVATED_V1,
      workspaceId: ctx.workspaceId,
      projectId,
      aggregateType: "project_agent_assignment",
      aggregateId: row.id.toString(),
      correlationId: randomUUID(),
      actor: { kind: "user", id: ctx.workforceMemberId ?? "system" },
      classification: "internal",
      payload: {
        workspaceId: ctx.workspaceId,
        projectId,
        assignmentId: row.id.toString(),
        profileKey,
        version: nextVersion,
        actorId: ctx.workforceMemberId ?? "system",
      },
    });
    await appendOutboxEvent(tx, envelope);

    return {
      profileKey: profileDef.key,
      label: profileDef.label,
      displayState: "ACTIVE",
      runtimeReadiness: profileDef.runtimeReadiness,
      assignmentVersion: nextVersion,
      activatedAt: now.toISOString(),
      activatedBy: actorId.toString(),
    };
  });
}

export interface PauseProjectStartupTeamMemberInput {
  expectedVersion: number;
  reason?: string;
  idempotencyKey?: string;
}

/**
 * Tạm dừng agent member của Project (Founder/Admin governed).
 */
export async function pauseProjectStartupTeamMember(
  ctx: TenantContext,
  projectId: string,
  profileKey: string,
  input: PauseProjectStartupTeamMemberInput
): Promise<ProjectStartupTeamMember> {
  await requireStartupTeamAuthority(ctx, projectId);

  if (profileKey === "founder_assistant") {
    throw APIError.invalidArgument(
      "founder_assistant is always available as chat co-founder and cannot be paused"
    );
  }

  if (!isStartupTeamProfileKey(profileKey)) {
    throw APIError.notFound(`Unknown profile key '${profileKey}'`);
  }

  const profileDef = STARTUP_TEAM_PROFILES.find((p) => p.key === profileKey);
  if (!profileDef) {
    throw APIError.notFound(`Profile '${profileKey}' not found in catalog`);
  }

  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);
  const actorId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : BigInt(0);

  return await db.transaction(async (tx) => {
    const [row] = await tx
      .select()
      .from(projectAgentAssignments)
      .where(
        and(
          eq(projectAgentAssignments.workspaceId, wsId),
          eq(projectAgentAssignments.projectId, projId),
          eq(projectAgentAssignments.profileKey, profileKey)
        )
      )
      .for("update")
      .limit(1);

    if (!row) {
      throw APIError.notFound(`Assignment for '${profileKey}' not found`);
    }

    if (input.idempotencyKey) {
      const existingEvents = await tx
        .select()
        .from(projectAgentAssignmentEvents)
        .where(
          and(
            eq(projectAgentAssignmentEvents.workspaceId, wsId),
            eq(projectAgentAssignmentEvents.projectId, projId),
            eq(projectAgentAssignmentEvents.assignmentId, row.id),
            eq(projectAgentAssignmentEvents.eventType, "ASSIGNMENT_PAUSED")
          )
        );
      const match = existingEvents.find(
        (e) => (e.eventPayload as any)?.idempotencyKey === input.idempotencyKey
      );
      if (match) {
        return {
          profileKey: profileDef.key,
          label: profileDef.label,
          displayState: row.state,
          runtimeReadiness: profileDef.runtimeReadiness,
          disabledReason: row.disabledReason ?? undefined,
          assignmentVersion: row.version,
          activatedAt: row.activatedAt ? row.activatedAt.toISOString() : undefined,
          activatedBy: row.activatedBy ? row.activatedBy.toString() : undefined,
        };
      }
    }

    if (row.version !== input.expectedVersion) {
      throw APIError.aborted(
        `Version conflict: expected version ${input.expectedVersion}, current version is ${row.version}`
      );
    }

    const nextVersion = row.version + 1;
    const now = new Date();
    const disabledReason = input.reason ?? "PAUSED_BY_FOUNDER";

    await tx
      .update(projectAgentAssignments)
      .set({
        state: "PAUSED",
        version: nextVersion,
        pausedAt: now,
        pausedBy: actorId,
        disabledReason,
        updatedAt: now,
      })
      .where(eq(projectAgentAssignments.id, row.id));

    await tx.insert(projectAgentAssignmentEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: projId,
      assignmentId: row.id,
      eventType: "ASSIGNMENT_PAUSED",
      fromState: row.state,
      toState: "PAUSED",
      assignmentVersion: nextVersion,
      actorId,
      occurredAt: now,
      eventPayload: {
        profileKey,
        reason: disabledReason,
        idempotencyKey: input.idempotencyKey ?? null,
        label: `${profileDef.label} paused`,
      },
    });

    const envelope = makeBusinessEvent({
      eventType: OPERATIONS_PROJECT_AGENT_ASSIGNMENT_PAUSED_V1,
      workspaceId: ctx.workspaceId,
      projectId,
      aggregateType: "project_agent_assignment",
      aggregateId: row.id.toString(),
      correlationId: randomUUID(),
      actor: { kind: "user", id: ctx.workforceMemberId ?? "system" },
      classification: "internal",
      payload: {
        workspaceId: ctx.workspaceId,
        projectId,
        assignmentId: row.id.toString(),
        profileKey,
        version: nextVersion,
        actorId: ctx.workforceMemberId ?? "system",
      },
    });
    await appendOutboxEvent(tx, envelope);

    return {
      profileKey: profileDef.key,
      label: profileDef.label,
      displayState: "PAUSED",
      runtimeReadiness: profileDef.runtimeReadiness,
      disabledReason,
      assignmentVersion: nextVersion,
      activatedAt: row.activatedAt ? row.activatedAt.toISOString() : undefined,
      activatedBy: row.activatedBy ? row.activatedBy.toString() : undefined,
    };
  });
}

export interface ProjectAgentRunAuthority {
  projectId: string;
  workspaceId: string;
  profileKey: StartupTeamProfileKey;
  assignmentVersion: number;
  agentWorkforceMemberId: string;
  spec: {
    id: string;
    version: string;
    hash: string;
  };
  policySnapshot: Record<string, unknown>;
}

/**
 * Run-authority read dành riêng cho Agent Platform (internal route).
 * Trả về 404 trừ khi assignment là ACTIVE và profile hiện tại READY.
 */
export async function getProjectAgentRunAuthority(
  workspaceId: string,
  projectId: string,
  profileKey: string
): Promise<ProjectAgentRunAuthority> {
  if (!isStartupTeamProfileKey(profileKey)) {
    throw APIError.notFound(`Unknown profile key '${profileKey}'`);
  }

  if (profileKey === "founder_assistant") {
    throw APIError.notFound("founder_assistant is not an assignable operating agent");
  }

  const profileDef = STARTUP_TEAM_PROFILES.find((p) => p.key === profileKey);
  if (!profileDef || profileDef.runtimeReadiness !== "READY") {
    throw APIError.notFound(`Profile '${profileKey}' is not ready for execution`);
  }

  const wsId = BigInt(workspaceId);
  const projId = BigInt(projectId);

  const [project] = await db
    .select({ id: projects.id, workspaceId: projects.workspaceId })
    .from(projects)
    .where(eq(projects.id, projId))
    .limit(1);

  if (!project) {
    throw APIError.notFound("Project not found");
  }
  // Trả 404 như project không tồn tại: không để lộ project của workspace khác.
  if (project.workspaceId !== wsId) {
    throw APIError.notFound("Project not found");
  }

  const [row] = await db
    .select()
    .from(projectAgentAssignments)
    .where(
      and(
        eq(projectAgentAssignments.workspaceId, wsId),
        eq(projectAgentAssignments.projectId, projId),
        eq(projectAgentAssignments.profileKey, profileKey)
      )
    )
    .limit(1);

  if (!row || row.state !== "ACTIVE" || !row.agentWorkforceMemberId) {
    throw APIError.notFound(
      `Agent '${profileKey}' is not actively assigned to project`
    );
  }

  return {
    projectId,
    workspaceId,
    profileKey: profileDef.key,
    assignmentVersion: row.version,
    agentWorkforceMemberId: row.agentWorkforceMemberId.toString(),
    spec: {
      id: row.specId ?? "",
      version: row.specVersion ?? "",
      hash: row.specHash ?? "",
    },
    policySnapshot: (row.activationPolicySnapshot as Record<string, unknown>) ?? {},
  };
}
