import { APIError } from "encore.dev/api";
import { eq, and, isNull, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";
import { getWorkspaceStrategySettings } from "../strategy/services/workspace-strategy-settings.service";
import { requireStrategyGovernanceAuthority } from "../strategy/services/strategy-governance-authorization.service";

const {
  initiatives,
  initiativeKeyResults,
  keyResults,
  strategicObjectives,
  towsOptions,
  projects,
  decisionRecords,
} = schema;

export interface InitiativeMilestone {
  id?: string;
  title: string;
  targetDate?: string;
  status?: string;
}

export interface Initiative {
  id: string;
  workspaceId: string;
  projectId: string | null;
  strategicObjectiveId: string | null;
  sourceTowsOptionId: string | null;
  title: string;
  description: string | null;
  intendedOutcome: string | null;
  startDate: string | null;
  targetDate: string | null;
  milestones: InitiativeMilestone[];
  status: string;
  approvalStatus: string;
  approvedByMemberId: string | null;
  approvedAt: string | null;
  decisionId: string | null;
  settingsRevision: number | null;
  ownerMemberId: string | null;
  revision: number;
  keyResultIds: string[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateInitiativeParams {
  workspaceId: string;
  projectId?: string;
  strategicObjectiveId?: string;
  sourceTowsOptionId?: string;
  title: string;
  description?: string;
  intendedOutcome?: string;
  startDate?: string;
  targetDate?: string;
  milestones?: InitiativeMilestone[];
  ownerMemberId?: string;
  keyResultIds?: string[];
  status?: string;
}

export interface UpdateInitiativeParams {
  id: string;
  workspaceId: string;
  projectId?: string;
  strategicObjectiveId?: string;
  sourceTowsOptionId?: string;
  title?: string;
  description?: string;
  intendedOutcome?: string;
  startDate?: string;
  targetDate?: string;
  milestones?: InitiativeMilestone[];
  status?: string;
  approvalStatus?: string;

  ownerMemberId?: string;
  keyResultIds?: string[];
  expectedRevision?: number;
}

export interface ApproveInitiativeParams {
  id: string;
  reason?: string;
}

export interface ListInitiativesParams {
  workspaceId: string;
  projectId?: string;
  strategicObjectiveId?: string;
  approvalStatus?: string;
}

function toInitiative(
  row: typeof initiatives.$inferSelect,
  keyResultIds: string[] = []
): Initiative {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId ? row.projectId.toString() : null,
    strategicObjectiveId: row.strategicObjectiveId
      ? row.strategicObjectiveId.toString()
      : null,
    sourceTowsOptionId: row.sourceTowsOptionId
      ? row.sourceTowsOptionId.toString()
      : null,
    title: row.title,
    description: row.description,
    intendedOutcome: row.intendedOutcome,
    startDate: row.startDate ? row.startDate.toISOString() : null,
    targetDate: row.targetDate ? row.targetDate.toISOString() : null,
    milestones: (row.milestones as any[]) || [],
    status: row.status,
    approvalStatus: row.approvalStatus,
    approvedByMemberId: row.approvedByMemberId
      ? row.approvedByMemberId.toString()
      : null,
    approvedAt: row.approvedAt ? row.approvedAt.toISOString() : null,
    decisionId: row.decisionId ? row.decisionId.toString() : null,
    settingsRevision: row.settingsRevision ?? null,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    revision: row.revision,
    keyResultIds,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

/**
 * Reusable helper to assert an Initiative exists in the caller workspace, is not soft-deleted,
 * and belongs to the workspace. Throws APIError.notFound if missing or cross-workspace.
 */
export async function assertInitiativeInWorkspace(
  id: string | number | bigint,
  workspaceId: string | number | bigint,
  requireApproved: boolean = false
): Promise<typeof initiatives.$inferSelect> {
  const wsId = BigInt(workspaceId);
  const initId = BigInt(id);

  const [row] = await db
    .select()
    .from(initiatives)
    .where(
      and(
        eq(initiatives.id, initId),
        eq(initiatives.workspaceId, wsId),
        isNull(initiatives.deletedAt)
      )
    )
    .limit(1);

  if (!row) {
    throw APIError.notFound(`Initiative ${id} not found in workspace`);
  }

  if (requireApproved && row.approvalStatus !== "APPROVED") {
    throw APIError.failedPrecondition(
      `Initiative ${id} must be APPROVED for strategic execution (current status: ${row.approvalStatus})`
    );
  }

  return row;
}


export async function createInitiativeService(
  params: CreateInitiativeParams,
  authorization: string | undefined
): Promise<Initiative> {
  await requireWorkspaceAccess(authorization, params.workspaceId);
  await getWorkspace({ id: params.workspaceId });

  const wsId = BigInt(params.workspaceId);

  if (!params.title || params.title.trim().length === 0) {
    throw APIError.invalidArgument("title is required");
  }

  let stratObjId: bigint | null = null;
  let sourceTowsId: bigint | null = null;
  let projId: bigint | null = null;

  if (params.strategicObjectiveId) {
    stratObjId = BigInt(params.strategicObjectiveId);
    const [stratObj] = await db
      .select()
      .from(strategicObjectives)
      .where(
        and(
          eq(strategicObjectives.id, stratObjId),
          eq(strategicObjectives.workspaceId, wsId)
        )
      )
      .limit(1);

    if (!stratObj) {
      throw APIError.notFound(
        `Strategic objective ${params.strategicObjectiveId} not found in workspace`
      );
    }

    if (params.sourceTowsOptionId) {
      sourceTowsId = BigInt(params.sourceTowsOptionId);
      const [towsOpt] = await db
        .select()
        .from(towsOptions)
        .where(
          and(
            eq(towsOptions.id, sourceTowsId),
            eq(towsOptions.workspaceId, wsId)
          )
        )
        .limit(1);

      if (!towsOpt) {
        throw APIError.notFound(
          `TOWS option ${params.sourceTowsOptionId} not found in workspace`
        );
      }

      if (towsOpt.strategicObjectiveId !== stratObjId) {
        throw APIError.invalidArgument(
          "Source TOWS option does not belong to specified strategic objective"
        );
      }

      if (towsOpt.status !== "SELECTED") {
        throw APIError.failedPrecondition(
          `Source TOWS option must be SELECTED (current status: ${towsOpt.status})`
        );
      }
    }
  }

  if (params.projectId) {
    projId = BigInt(params.projectId);
    const [proj] = await db
      .select()
      .from(projects)
      .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
      .limit(1);

    if (!proj) {
      throw APIError.notFound(`Project ${params.projectId} not found in workspace`);
    }
  }

  const krIds = params.keyResultIds || [];
  if (krIds.length > 0) {
    const krBigInts = krIds.map((k) => BigInt(k));
    const krRows = await db
      .select()
      .from(keyResults)
      .where(
        and(
          eq(keyResults.workspaceId, wsId),
          inArray(keyResults.id, krBigInts),
          isNull(keyResults.deletedAt)
        )
      );

    if (krRows.length !== krIds.length) {
      throw APIError.invalidArgument(
        "One or more Key Results do not belong to caller workspace"
      );
    }
  }

  const id = generateSnowflake();

  const [row] = await db
    .insert(initiatives)
    .values({
      id,
      workspaceId: wsId,
      projectId: projId,
      strategicObjectiveId: stratObjId,
      sourceTowsOptionId: sourceTowsId,
      title: params.title.trim(),
      description: params.description || null,
      intendedOutcome: params.intendedOutcome || null,
      startDate: params.startDate ? new Date(params.startDate) : null,
      targetDate: params.targetDate ? new Date(params.targetDate) : null,
      milestones: params.milestones || [],
      status: params.status || "active",
      approvalStatus: "DRAFT",
      ownerMemberId: params.ownerMemberId ? BigInt(params.ownerMemberId) : null,
      revision: 1,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create initiative");

  if (krIds.length > 0) {
    await db.insert(initiativeKeyResults).values(
      krIds.map((krId) => ({
        workspaceId: wsId,
        initiativeId: id,
        keyResultId: BigInt(krId),
      }))
    );
  }

  return toInitiative(row, krIds);
}

export async function updateInitiativeService(
  params: UpdateInitiativeParams,
  ctx: TenantContext
): Promise<Initiative> {
  const wsId = BigInt(ctx.workspaceId);
  const existing = await assertInitiativeInWorkspace(params.id, wsId);

  if (
    params.expectedRevision !== undefined &&
    existing.revision !== params.expectedRevision
  ) {
    throw APIError.aborted(
      `Revision conflict: current revision is ${existing.revision}, expected ${params.expectedRevision}`
    );
  }

  let stratObjId = existing.strategicObjectiveId;
  let sourceTowsId = existing.sourceTowsOptionId;
  let projId = existing.projectId;

  if (params.strategicObjectiveId !== undefined) {
    if (params.strategicObjectiveId === null || params.strategicObjectiveId === "") {
      stratObjId = null;
      sourceTowsId = null;
    } else {
      stratObjId = BigInt(params.strategicObjectiveId);
      const [stratObj] = await db
        .select()
        .from(strategicObjectives)
        .where(
          and(
            eq(strategicObjectives.id, stratObjId),
            eq(strategicObjectives.workspaceId, wsId)
          )
        )
        .limit(1);

      if (!stratObj) {
        throw APIError.notFound(
          `Strategic objective ${params.strategicObjectiveId} not found in workspace`
        );
      }
    }
  }

  if (params.sourceTowsOptionId !== undefined) {
    if (params.sourceTowsOptionId === null || params.sourceTowsOptionId === "") {
      sourceTowsId = null;
    } else {
      sourceTowsId = BigInt(params.sourceTowsOptionId);
      const [towsOpt] = await db
        .select()
        .from(towsOptions)
        .where(
          and(
            eq(towsOptions.id, sourceTowsId),
            eq(towsOptions.workspaceId, wsId)
          )
        )
        .limit(1);

      if (!towsOpt) {
        throw APIError.notFound(
          `TOWS option ${params.sourceTowsOptionId} not found in workspace`
        );
      }

      if (stratObjId && towsOpt.strategicObjectiveId !== stratObjId) {
        throw APIError.invalidArgument(
          "Source TOWS option does not belong to specified strategic objective"
        );
      }
    }
  }

  if (params.projectId !== undefined) {
    if (params.projectId === null || params.projectId === "") {
      projId = null;
    } else {
      projId = BigInt(params.projectId);
      const [proj] = await db
        .select()
        .from(projects)
        .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
        .limit(1);

      if (!proj) {
        throw APIError.notFound(`Project ${params.projectId} not found in workspace`);
      }
    }
  }

  let finalKrIds: string[];
  if (params.keyResultIds !== undefined) {
    finalKrIds = params.keyResultIds;
    if (finalKrIds.length > 0) {
      const krBigInts = finalKrIds.map((k) => BigInt(k));
      const krRows = await db
        .select()
        .from(keyResults)
        .where(
          and(
            eq(keyResults.workspaceId, wsId),
            inArray(keyResults.id, krBigInts),
            isNull(keyResults.deletedAt)
          )
        );

      if (krRows.length !== finalKrIds.length) {
        throw APIError.invalidArgument(
          "One or more Key Results do not belong to caller workspace"
        );
      }
    }

    // Replace linked key results
    await db
      .delete(initiativeKeyResults)
      .where(
        and(
          eq(initiativeKeyResults.workspaceId, wsId),
          eq(initiativeKeyResults.initiativeId, existing.id)
        )
      );

    if (finalKrIds.length > 0) {
      await db.insert(initiativeKeyResults).values(
        finalKrIds.map((krId) => ({
          workspaceId: wsId,
          initiativeId: existing.id,
          keyResultId: BigInt(krId),
        }))
      );
    }
  } else {
    const linkedKrs = await db
      .select({ keyResultId: initiativeKeyResults.keyResultId })
      .from(initiativeKeyResults)
      .where(
        and(
          eq(initiativeKeyResults.workspaceId, wsId),
          eq(initiativeKeyResults.initiativeId, existing.id)
        )
      );
    finalKrIds = linkedKrs.map((l) => l.keyResultId.toString());
  }

  const [updated] = await db
    .update(initiatives)
    .set({
      projectId: projId,
      strategicObjectiveId: stratObjId,
      sourceTowsOptionId: sourceTowsId,
      title: params.title !== undefined ? params.title.trim() : existing.title,
      description:
        params.description !== undefined
          ? params.description
          : existing.description,
      intendedOutcome:
        params.intendedOutcome !== undefined
          ? params.intendedOutcome
          : existing.intendedOutcome,
      startDate:
        params.startDate !== undefined
          ? params.startDate
            ? new Date(params.startDate)
            : null
          : existing.startDate,
      targetDate:
        params.targetDate !== undefined
          ? params.targetDate
            ? new Date(params.targetDate)
            : null
          : existing.targetDate,
      milestones:
        params.milestones !== undefined
          ? params.milestones
          : existing.milestones,
      status: params.status !== undefined ? params.status : existing.status,
      approvalStatus:
        params.approvalStatus !== undefined
          ? params.approvalStatus
          : existing.approvalStatus,
      ownerMemberId:
        params.ownerMemberId !== undefined
          ? params.ownerMemberId
            ? BigInt(params.ownerMemberId)
            : null
          : existing.ownerMemberId,
      revision: existing.revision + 1,
      updatedAt: new Date(),
    })
    .where(eq(initiatives.id, existing.id))
    .returning();

  return toInitiative(updated, finalKrIds);
}

export async function approveInitiativeService(
  params: ApproveInitiativeParams,
  ctx: TenantContext
): Promise<Initiative> {
  const wsId = BigInt(ctx.workspaceId);
  const existing = await assertInitiativeInWorkspace(params.id, wsId);

  // Require strategy governance authority
  await requireStrategyGovernanceAuthority(ctx, "strategy.initiative.approve", {
    workspaceId: ctx.workspaceId,
  });

  if (["APPROVED", "REJECTED", "CLOSED"].includes(existing.approvalStatus)) {
    throw APIError.failedPrecondition(
      `Cannot approve initiative with status ${existing.approvalStatus}`
    );
  }

  const settings = await getWorkspaceStrategySettings(ctx.workspaceId);
  const actorId = ctx.workforceMemberId
    ? BigInt(ctx.workforceMemberId)
    : ctx.userId
    ? BigInt(ctx.userId)
    : null;

  const decisionId = generateSnowflake();

  await db.insert(decisionRecords).values({
    id: decisionId,
    workspaceId: wsId,
    projectId: existing.projectId,
    decision: "INITIATIVE_APPROVED",
    decisionType: "INITIATIVE_APPROVAL",
    createdByKind: "FOUNDER",
    policyVersion: String(settings.revision),
    actorMemberId: actorId,
    founderDecision: "accepted",
    decidedAt: new Date(),
    evidenceSnapshot: {
      action: "INITIATIVE_APPROVED",
      initiativeId: existing.id.toString(),
      strategicObjectiveId: existing.strategicObjectiveId?.toString() ?? null,
      sourceTowsOptionId: existing.sourceTowsOptionId?.toString() ?? null,
      reason: params.reason || "",
      settingsRevision: settings.revision,
      approver: {
        memberId: actorId ? actorId.toString() : null,
        role: ctx.membershipRole,
      },
      recordedAt: new Date().toISOString(),
    },
  });

  const [updated] = await db
    .update(initiatives)
    .set({
      approvalStatus: "APPROVED",
      approvedByMemberId: actorId,
      approvedAt: new Date(),
      decisionId,
      settingsRevision: settings.revision,
      revision: existing.revision + 1,
      updatedAt: new Date(),
    })
    .where(eq(initiatives.id, existing.id))
    .returning();

  const linkedKrs = await db
    .select({ keyResultId: initiativeKeyResults.keyResultId })
    .from(initiativeKeyResults)
    .where(
      and(
        eq(initiativeKeyResults.workspaceId, wsId),
        eq(initiativeKeyResults.initiativeId, existing.id)
      )
    );

  return toInitiative(
    updated,
    linkedKrs.map((l) => l.keyResultId.toString())
  );
}

export async function getInitiativeService(
  id: string,
  authorization: string | undefined
): Promise<Initiative> {
  const [row] = await db
    .select()
    .from(initiatives)
    .where(eq(initiatives.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`initiative ${id} not found`);
  await requireWorkspaceAccess(authorization, row.workspaceId.toString());

  const linkedKrs = await db
    .select({ keyResultId: initiativeKeyResults.keyResultId })
    .from(initiativeKeyResults)
    .where(
      and(
        eq(initiativeKeyResults.workspaceId, row.workspaceId),
        eq(initiativeKeyResults.initiativeId, row.id)
      )
    );

  return toInitiative(
    row,
    linkedKrs.map((l) => l.keyResultId.toString())
  );
}

export async function listInitiativesService(
  params: ListInitiativesParams,
  ctx: TenantContext
): Promise<{ items: Initiative[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const conditions = [
    eq(initiatives.workspaceId, wsId),
    isNull(initiatives.deletedAt),
  ];

  if (params.projectId) {
    conditions.push(eq(initiatives.projectId, BigInt(params.projectId)));
  }

  if (params.strategicObjectiveId) {
    conditions.push(
      eq(initiatives.strategicObjectiveId, BigInt(params.strategicObjectiveId))
    );
  }

  if (params.approvalStatus) {
    conditions.push(eq(initiatives.approvalStatus, params.approvalStatus));
  }

  const rows = await db
    .select()
    .from(initiatives)
    .where(and(...conditions));

  if (rows.length === 0) {
    return { items: [] };
  }

  const initIds = rows.map((r) => r.id);
  const linkedRows = await db
    .select({
      initiativeId: initiativeKeyResults.initiativeId,
      keyResultId: initiativeKeyResults.keyResultId,
    })
    .from(initiativeKeyResults)
    .where(
      and(
        eq(initiativeKeyResults.workspaceId, wsId),
        inArray(initiativeKeyResults.initiativeId, initIds)
      )
    );

  const krsByInitId = new Map<string, string[]>();
  for (const lr of linkedRows) {
    const iId = lr.initiativeId.toString();
    const existing = krsByInitId.get(iId) || [];
    existing.push(lr.keyResultId.toString());
    krsByInitId.set(iId, existing);
  }

  return {
    items: rows.map((r) =>
      toInitiative(r, krsByInitId.get(r.id.toString()) || [])
    ),
  };
}
