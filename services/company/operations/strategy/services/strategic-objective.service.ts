import { eq, and } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../../models/db";
import {
  strategicObjectives,
  bscFocusScopes,
  projects,
} from "../../../shared/db/schema";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { TenantContext } from "../../../shared/types/tenant_context";
import {
  BscPerspective,
  VALID_BSC_PERSPECTIVES,
  getWorkspaceStrategySettings,
} from "./workspace-strategy-settings.service";

export type StrategicObjectiveStatus = "DRAFT" | "ACTIVE" | "ARCHIVED";
export type BscFocusScopeStatus = "ACTIVE" | "INACTIVE" | "ARCHIVED";

export interface BscFocusScope {
  id: string;
  workspaceId: string;
  strategicObjectiveId: string;
  perspective: BscPerspective;
  focusQuestion?: string | null;
  focusStatement: string;
  priority: number;
  status: BscFocusScopeStatus;
  revision: number;
  createdAt: string;
  updatedAt: string;
}

export interface StrategicObjective {
  id: string;
  workspaceId: string;
  projectId?: string | null;
  title: string;
  successDefinition?: string | null;
  timeHorizonEnd?: string | null;
  status: StrategicObjectiveStatus;
  ownerMemberId?: string | null;
  settingsRevision?: number | null;
  createdByMemberId?: string | null;
  updatedByMemberId?: string | null;
  revision: number;
  createdAt: string;
  updatedAt: string;
  bscFocusScopes?: BscFocusScope[];
}

export interface CreateStrategicObjectiveInput {
  workspaceId: string;
  projectId?: string | null;
  title: string;
  successDefinition?: string | null;
  timeHorizonEnd?: string | null;
  status?: StrategicObjectiveStatus;
  ownerMemberId?: string | null;
}

export interface UpdateStrategicObjectiveInput {
  workspaceId: string;
  id: string;
  projectId?: string | null;
  title?: string;
  successDefinition?: string | null;
  timeHorizonEnd?: string | null;
  status?: StrategicObjectiveStatus;
  ownerMemberId?: string | null;
  expectedRevision?: number;
}

export interface SaveBscFocusScopeItem {
  id?: string;
  perspective: BscPerspective;
  focusQuestion?: string | null;
  focusStatement: string;
  priority?: number;
  status?: BscFocusScopeStatus;
}

export async function assertProjectInWorkspace(
  projectId: bigint | string,
  workspaceId: bigint | string
): Promise<void> {
  const pId = BigInt(projectId);
  const wsId = BigInt(workspaceId);

  const [row] = await db
    .select({ id: projects.id, workspaceId: projects.workspaceId })
    .from(projects)
    .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!row) {
    throw APIError.invalidArgument(
      `Project ${projectId} does not exist in workspace ${workspaceId}`
    );
  }
}

export async function createStrategicObjective(
  ctx: TenantContext,
  params: CreateStrategicObjectiveInput
): Promise<StrategicObjective> {
  const wsId = BigInt(params.workspaceId);

  if (!params.title || params.title.trim().length === 0) {
    throw APIError.invalidArgument("Strategic objective title cannot be empty");
  }

  if (params.projectId) {
    await assertProjectInWorkspace(params.projectId, wsId);
  }

  const status = params.status || "DRAFT";
  let settingsRevision: number | null = null;

  if (status === "ACTIVE") {
    if (!params.successDefinition || params.successDefinition.trim().length === 0) {
      throw APIError.invalidArgument(
        "A strategic objective cannot become active without a success definition describing a measurable end state"
      );
    }
    const settings = await getWorkspaceStrategySettings(params.workspaceId);
    if (settings.bscMode === "REQUIRED") {
      throw APIError.failedPrecondition(
        "Strategic objective requires at least one active BSC focus scope before activation under REQUIRED mode"
      );
    }
    settingsRevision = settings.revision;
  }

  const id = generateSnowflake();
  const now = new Date();
  const creatorId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;
  const ownerId = params.ownerMemberId ? BigInt(params.ownerMemberId) : creatorId;

  const [row] = await db
    .insert(strategicObjectives)
    .values({
      id,
      workspaceId: wsId,
      projectId: params.projectId ? BigInt(params.projectId) : null,
      title: params.title.trim(),
      successDefinition: params.successDefinition?.trim() || null,
      timeHorizonEnd: params.timeHorizonEnd ? new Date(params.timeHorizonEnd) : null,
      status,
      ownerMemberId: ownerId,
      settingsRevision,
      createdByMemberId: creatorId,
      updatedByMemberId: creatorId,
      revision: 1,
      createdAt: now,
      updatedAt: now,
    })
    .returning();

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId ? row.projectId.toString() : null,
    title: row.title,
    successDefinition: row.successDefinition,
    timeHorizonEnd: row.timeHorizonEnd ? row.timeHorizonEnd.toISOString() : null,
    status: row.status as StrategicObjectiveStatus,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    settingsRevision: row.settingsRevision,
    createdByMemberId: row.createdByMemberId ? row.createdByMemberId.toString() : null,
    updatedByMemberId: row.updatedByMemberId ? row.updatedByMemberId.toString() : null,
    revision: row.revision,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
    bscFocusScopes: [],
  };
}

export async function getStrategicObjective(
  workspaceId: bigint | string,
  id: bigint | string
): Promise<StrategicObjective> {
  const wsId = BigInt(workspaceId);
  const objId = BigInt(id);

  const [row] = await db
    .select()
    .from(strategicObjectives)
    .where(and(eq(strategicObjectives.id, objId), eq(strategicObjectives.workspaceId, wsId)))
    .limit(1);

  if (!row) {
    throw APIError.notFound(`Strategic objective ${id} not found in workspace`);
  }

  const scopes = await db
    .select()
    .from(bscFocusScopes)
    .where(
      and(
        eq(bscFocusScopes.strategicObjectiveId, objId),
        eq(bscFocusScopes.workspaceId, wsId)
      )
    );

  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId ? row.projectId.toString() : null,
    title: row.title,
    successDefinition: row.successDefinition,
    timeHorizonEnd: row.timeHorizonEnd ? row.timeHorizonEnd.toISOString() : null,
    status: row.status as StrategicObjectiveStatus,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    settingsRevision: row.settingsRevision,
    createdByMemberId: row.createdByMemberId ? row.createdByMemberId.toString() : null,
    updatedByMemberId: row.updatedByMemberId ? row.updatedByMemberId.toString() : null,
    revision: row.revision,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
    bscFocusScopes: scopes.map((s) => ({
      id: s.id.toString(),
      workspaceId: s.workspaceId.toString(),
      strategicObjectiveId: s.strategicObjectiveId.toString(),
      perspective: s.perspective as BscPerspective,
      focusQuestion: s.focusQuestion,
      focusStatement: s.focusStatement,
      priority: s.priority,
      status: s.status as BscFocusScopeStatus,
      revision: s.revision,
      createdAt: s.createdAt.toISOString(),
      updatedAt: s.updatedAt.toISOString(),
    })),
  };
}

export async function listStrategicObjectives(params: {
  workspaceId: bigint | string;
  projectId?: bigint | string | null;
  status?: StrategicObjectiveStatus;
}): Promise<{ items: StrategicObjective[] }> {
  const wsId = BigInt(params.workspaceId);

  const conditions = [eq(strategicObjectives.workspaceId, wsId)];

  if (params.projectId) {
    conditions.push(eq(strategicObjectives.projectId, BigInt(params.projectId)));
  }

  if (params.status) {
    conditions.push(eq(strategicObjectives.status, params.status));
  }

  const rows = await db
    .select()
    .from(strategicObjectives)
    .where(and(...conditions));

  return {
    items: rows.map((row) => ({
      id: row.id.toString(),
      workspaceId: row.workspaceId.toString(),
      projectId: row.projectId ? row.projectId.toString() : null,
      title: row.title,
      successDefinition: row.successDefinition,
      timeHorizonEnd: row.timeHorizonEnd ? row.timeHorizonEnd.toISOString() : null,
      status: row.status as StrategicObjectiveStatus,
      ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
      settingsRevision: row.settingsRevision,
      createdByMemberId: row.createdByMemberId ? row.createdByMemberId.toString() : null,
      updatedByMemberId: row.updatedByMemberId ? row.updatedByMemberId.toString() : null,
      revision: row.revision,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    })),
  };
}

export async function updateStrategicObjective(
  ctx: TenantContext,
  params: UpdateStrategicObjectiveInput
): Promise<StrategicObjective> {
  const wsId = BigInt(params.workspaceId);
  const objId = BigInt(params.id);

  const [existing] = await db
    .select()
    .from(strategicObjectives)
    .where(and(eq(strategicObjectives.id, objId), eq(strategicObjectives.workspaceId, wsId)))
    .limit(1);

  if (!existing) {
    throw APIError.notFound(`Strategic objective ${params.id} not found in workspace`);
  }

  if (existing.status === "ARCHIVED") {
    throw APIError.failedPrecondition("Cannot update an archived strategic objective");
  }

  if (params.expectedRevision !== undefined && existing.revision !== params.expectedRevision) {
    throw APIError.aborted(
      `Objective revision conflict: expected ${params.expectedRevision}, current is ${existing.revision}`
    );
  }

  const newProjectId =
    params.projectId !== undefined
      ? params.projectId
        ? BigInt(params.projectId)
        : null
      : existing.projectId;

  if (params.projectId && params.projectId !== (existing.projectId ? existing.projectId.toString() : null)) {
    await assertProjectInWorkspace(params.projectId, wsId);
  }

  const newTitle = params.title !== undefined ? params.title.trim() : existing.title;
  if (!newTitle) {
    throw APIError.invalidArgument("Strategic objective title cannot be empty");
  }

  const newSuccessDef =
    params.successDefinition !== undefined
      ? params.successDefinition?.trim() || null
      : existing.successDefinition;

  const newStatus = params.status || (existing.status as StrategicObjectiveStatus);
  let newSettingsRevision = existing.settingsRevision;

  if (newStatus === "ACTIVE") {
    if (!newSuccessDef || newSuccessDef.length === 0) {
      throw APIError.invalidArgument(
        "A strategic objective cannot become active without a success definition describing a measurable end state"
      );
    }

    const settings = await getWorkspaceStrategySettings(params.workspaceId);
    if (settings.bscMode === "REQUIRED") {
      const activeScopes = await db
        .select({ id: bscFocusScopes.id })
        .from(bscFocusScopes)
        .where(
          and(
            eq(bscFocusScopes.strategicObjectiveId, objId),
            eq(bscFocusScopes.workspaceId, wsId),
            eq(bscFocusScopes.status, "ACTIVE")
          )
        );

      if (activeScopes.length === 0) {
        throw APIError.failedPrecondition(
          "Strategic objective requires at least one active BSC focus scope before activation under REQUIRED mode"
        );
      }
    }
    newSettingsRevision = settings.revision;
  }

  const now = new Date();
  const updaterId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;

  const [row] = await db
    .update(strategicObjectives)
    .set({
      projectId: newProjectId,
      title: newTitle,
      successDefinition: newSuccessDef,
      timeHorizonEnd:
        params.timeHorizonEnd !== undefined
          ? params.timeHorizonEnd
            ? new Date(params.timeHorizonEnd)
            : null
          : existing.timeHorizonEnd,
      status: newStatus,
      ownerMemberId:
        params.ownerMemberId !== undefined
          ? params.ownerMemberId
            ? BigInt(params.ownerMemberId)
            : null
          : existing.ownerMemberId,
      settingsRevision: newSettingsRevision,
      updatedByMemberId: updaterId,
      revision: existing.revision + 1,
      updatedAt: now,
    })
    .where(and(eq(strategicObjectives.id, objId), eq(strategicObjectives.workspaceId, wsId)))
    .returning();

  return getStrategicObjective(wsId, row.id);
}

export async function saveBscFocusScopes(
  ctx: TenantContext,
  params: {
    workspaceId: string;
    strategicObjectiveId: string;
    scopes: SaveBscFocusScopeItem[];
  }
): Promise<BscFocusScope[]> {
  const wsId = BigInt(params.workspaceId);
  const objId = BigInt(params.strategicObjectiveId);

  // Validate objective exists and is not archived
  const [objective] = await db
    .select()
    .from(strategicObjectives)
    .where(and(eq(strategicObjectives.id, objId), eq(strategicObjectives.workspaceId, wsId)))
    .limit(1);

  if (!objective) {
    throw APIError.notFound(`Strategic objective ${params.strategicObjectiveId} not found`);
  }

  if (objective.status === "ARCHIVED") {
    throw APIError.failedPrecondition("Cannot add or update BSC focus scopes on an archived objective");
  }

  // Check workspace settings for enabled perspectives
  const settings = await getWorkspaceStrategySettings(params.workspaceId);
  const enabledSet = new Set(settings.enabledBscPerspectives);

  for (const item of params.scopes) {
    if (!VALID_BSC_PERSPECTIVES.includes(item.perspective)) {
      throw APIError.invalidArgument(`Invalid BSC perspective: '${item.perspective}'`);
    }

    if (
      settings.bscMode !== "OFF" &&
      settings.enabledBscPerspectives.length > 0 &&
      !enabledSet.has(item.perspective)
    ) {
      throw APIError.invalidArgument(
        `BSC perspective '${item.perspective}' is not enabled in workspace settings`
      );
    }
  }

  const now = new Date();
  const actorId = ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null;
  const results: BscFocusScope[] = [];

  for (const item of params.scopes) {
    const itemStatus = item.status || "ACTIVE";

    // If making ACTIVE, ensure existing active scopes for the same perspective are handled
    if (itemStatus === "ACTIVE") {
      if (item.id) {
        // Updating existing by id
        const scopeId = BigInt(item.id);
        const [existingScope] = await db
          .select()
          .from(bscFocusScopes)
          .where(
            and(
              eq(bscFocusScopes.id, scopeId),
              eq(bscFocusScopes.strategicObjectiveId, objId),
              eq(bscFocusScopes.workspaceId, wsId)
            )
          )
          .limit(1);

        if (existingScope) {
          // Deactivate any other active scope for this perspective
          await db
            .update(bscFocusScopes)
            .set({ status: "INACTIVE", updatedAt: now })
            .where(
              and(
                eq(bscFocusScopes.strategicObjectiveId, objId),
                eq(bscFocusScopes.workspaceId, wsId),
                eq(bscFocusScopes.perspective, item.perspective),
                eq(bscFocusScopes.status, "ACTIVE")
              )
            );

          const [updated] = await db
            .update(bscFocusScopes)
            .set({
              perspective: item.perspective,
              focusQuestion: item.focusQuestion ?? existingScope.focusQuestion,
              focusStatement: item.focusStatement,
              priority: item.priority ?? existingScope.priority,
              status: itemStatus,
              updatedByMemberId: actorId,
              revision: existingScope.revision + 1,
              updatedAt: now,
            })
            .where(eq(bscFocusScopes.id, scopeId))
            .returning();

          results.push({
            id: updated.id.toString(),
            workspaceId: updated.workspaceId.toString(),
            strategicObjectiveId: updated.strategicObjectiveId.toString(),
            perspective: updated.perspective as BscPerspective,
            focusQuestion: updated.focusQuestion,
            focusStatement: updated.focusStatement,
            priority: updated.priority,
            status: updated.status as BscFocusScopeStatus,
            revision: updated.revision,
            createdAt: updated.createdAt.toISOString(),
            updatedAt: updated.updatedAt.toISOString(),
          });
          continue;
        }
      }

      // Upsert: check if an active scope for this perspective already exists
      const [existingActive] = await db
        .select()
        .from(bscFocusScopes)
        .where(
          and(
            eq(bscFocusScopes.strategicObjectiveId, objId),
            eq(bscFocusScopes.workspaceId, wsId),
            eq(bscFocusScopes.perspective, item.perspective),
            eq(bscFocusScopes.status, "ACTIVE")
          )
        )
        .limit(1);

      if (existingActive) {
        const [updated] = await db
          .update(bscFocusScopes)
          .set({
            focusQuestion: item.focusQuestion ?? existingActive.focusQuestion,
            focusStatement: item.focusStatement,
            priority: item.priority ?? existingActive.priority,
            updatedByMemberId: actorId,
            revision: existingActive.revision + 1,
            updatedAt: now,
          })
          .where(eq(bscFocusScopes.id, existingActive.id))
          .returning();

        results.push({
          id: updated.id.toString(),
          workspaceId: updated.workspaceId.toString(),
          strategicObjectiveId: updated.strategicObjectiveId.toString(),
          perspective: updated.perspective as BscPerspective,
          focusQuestion: updated.focusQuestion,
          focusStatement: updated.focusStatement,
          priority: updated.priority,
          status: updated.status as BscFocusScopeStatus,
          revision: updated.revision,
          createdAt: updated.createdAt.toISOString(),
          updatedAt: updated.updatedAt.toISOString(),
        });
        continue;
      }
    }

    // Insert new scope
    const newId = generateSnowflake();
    const [inserted] = await db
      .insert(bscFocusScopes)
      .values({
        id: newId,
        workspaceId: wsId,
        strategicObjectiveId: objId,
        perspective: item.perspective,
        focusQuestion: item.focusQuestion || null,
        focusStatement: item.focusStatement,
        priority: item.priority || 1,
        status: itemStatus,
        createdByMemberId: actorId,
        updatedByMemberId: actorId,
        revision: 1,
        createdAt: now,
        updatedAt: now,
      })
      .returning();

    results.push({
      id: inserted.id.toString(),
      workspaceId: inserted.workspaceId.toString(),
      strategicObjectiveId: inserted.strategicObjectiveId.toString(),
      perspective: inserted.perspective as BscPerspective,
      focusQuestion: inserted.focusQuestion,
      focusStatement: inserted.focusStatement,
      priority: inserted.priority,
      status: inserted.status as BscFocusScopeStatus,
      revision: inserted.revision,
      createdAt: inserted.createdAt.toISOString(),
      updatedAt: inserted.updatedAt.toISOString(),
    });
  }

  return results;
}
