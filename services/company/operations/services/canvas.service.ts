import { APIError } from "encore.dev/api";
import { and, eq, isNull, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { mvpList, mvpItem, MvpSuccess, MvpSourceRef } from "../../shared/contracts/mvp-response";

const { canvases, canvasRevisions } = schema;

export interface Canvas {
  id: string;
  workspaceId: string;
  name: string;
  description: string | null;
  currentRevisionId: string | null;
  createdByMemberId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CanvasRevision {
  id: string;
  workspaceId: string;
  canvasId: string;
  parentRevisionId: string | null;
  content: Record<string, unknown>;
  status: "DRAFT" | "IN_REVIEW" | "APPROVED" | "REJECTED";
  origin: "USER" | "MODEL_DRAFT";
  sourceRefs: readonly MvpSourceRef[];
  createdByMemberId: string | null;
  reviewedByMemberId: string | null;
  reviewNote: string | null;
  createdAt: string;
  reviewedAt: string | null;
}

function mapCanvas(row: typeof canvases.$inferSelect): Canvas {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    name: row.name,
    description: row.description,
    currentRevisionId: row.currentRevisionId ? row.currentRevisionId.toString() : null,
    createdByMemberId: row.createdByMemberId ? row.createdByMemberId.toString() : null,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

function mapRevision(row: typeof canvasRevisions.$inferSelect): CanvasRevision {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    canvasId: row.canvasId.toString(),
    parentRevisionId: row.parentRevisionId ? row.parentRevisionId.toString() : null,
    content: (row.content || {}) as Record<string, unknown>,
    status: row.status as CanvasRevision["status"],
    origin: row.origin as CanvasRevision["origin"],
    sourceRefs: (row.sourceRefs || []) as unknown as readonly MvpSourceRef[],
    createdByMemberId: row.createdByMemberId ? row.createdByMemberId.toString() : null,
    reviewedByMemberId: row.reviewedByMemberId ? row.reviewedByMemberId.toString() : null,
    reviewNote: row.reviewNote,
    createdAt: row.createdAt.toISOString(),
    reviewedAt: row.reviewedAt ? row.reviewedAt.toISOString() : null,
  };
}

export async function listCanvasesService(ctx: TenantContext): Promise<MvpSuccess<readonly Canvas[]>> {
  const wsId = BigInt(ctx.workspaceId);
  const rows = await db
    .select()
    .from(canvases)
    .where(and(eq(canvases.workspaceId, wsId), isNull(canvases.deletedAt)))
    .orderBy(desc(canvases.updatedAt));

  return mvpList(
    rows.map(mapCanvas),
    [{ kind: "company_db", ref: "strategy.canvases" }]
  );
}

export async function createCanvasService(
  ctx: TenantContext,
  params: { name: string; description?: string | null }
): Promise<MvpSuccess<Canvas>> {
  if (!params.name || params.name.trim().length === 0) {
    throw APIError.invalidArgument("Canvas name cannot be empty");
  }

  const wsId = BigInt(ctx.workspaceId);
  const id = generateSnowflake();
  const now = new Date();

  const [inserted] = await db
    .insert(canvases)
    .values({
      id,
      workspaceId: wsId,
      name: params.name.trim(),
      description: params.description || null,
      createdByMemberId: ctx.memberId ? BigInt(ctx.memberId) : null,
      createdAt: now,
      updatedAt: now,
    })
    .returning();

  return mvpItem(mapCanvas(inserted), [{ kind: "company_db", ref: "strategy.canvases" }]);
}

export async function getCanvasService(ctx: TenantContext, idStr: string): Promise<MvpSuccess<Canvas>> {
  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(idStr);

  const [row] = await db
    .select()
    .from(canvases)
    .where(and(eq(canvases.id, id), eq(canvases.workspaceId, wsId), isNull(canvases.deletedAt)));

  if (!row) {
    throw APIError.notFound("Canvas not found");
  }

  return mvpItem(mapCanvas(row), [{ kind: "company_db", ref: "strategy.canvases" }]);
}

export async function updateCanvasService(
  ctx: TenantContext,
  idStr: string,
  params: { name?: string; description?: string | null }
): Promise<MvpSuccess<Canvas>> {
  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(idStr);

  const [existing] = await db
    .select()
    .from(canvases)
    .where(and(eq(canvases.id, id), eq(canvases.workspaceId, wsId), isNull(canvases.deletedAt)));

  if (!existing) {
    throw APIError.notFound("Canvas not found");
  }

  const updates: Partial<typeof canvases.$inferInsert> = {
    updatedAt: new Date(),
  };
  if (params.name !== undefined) {
    if (params.name.trim().length === 0) throw APIError.invalidArgument("Canvas name cannot be empty");
    updates.name = params.name.trim();
  }
  if (params.description !== undefined) {
    updates.description = params.description;
  }

  const [updated] = await db
    .update(canvases)
    .set(updates)
    .where(and(eq(canvases.id, id), eq(canvases.workspaceId, wsId)))
    .returning();

  return mvpItem(mapCanvas(updated), [{ kind: "company_db", ref: "strategy.canvases" }]);
}

export async function deleteCanvasService(ctx: TenantContext, idStr: string): Promise<void> {
  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(idStr);

  const [existing] = await db
    .select()
    .from(canvases)
    .where(and(eq(canvases.id, id), eq(canvases.workspaceId, wsId), isNull(canvases.deletedAt)));

  if (!existing) {
    throw APIError.notFound("Canvas not found");
  }

  await db
    .update(canvases)
    .set({ deletedAt: new Date() })
    .where(and(eq(canvases.id, id), eq(canvases.workspaceId, wsId)));
}

export async function createRevisionService(
  ctx: TenantContext,
  canvasIdStr: string,
  params: {
    content: Record<string, unknown>;
    origin: "USER" | "MODEL_DRAFT";
    sourceRefs?: readonly MvpSourceRef[];
    parentRevisionId?: string | null;
  }
): Promise<MvpSuccess<CanvasRevision>> {
  const wsId = BigInt(ctx.workspaceId);
  const canvasId = BigInt(canvasIdStr);

  // Validate canvas belongs to workspace
  const [canvas] = await db
    .select()
    .from(canvases)
    .where(and(eq(canvases.id, canvasId), eq(canvases.workspaceId, wsId), isNull(canvases.deletedAt)));

  if (!canvas) {
    throw APIError.notFound("Canvas not found");
  }

  if (params.origin === "MODEL_DRAFT") {
    if (!params.sourceRefs || params.sourceRefs.length === 0) {
      throw APIError.invalidArgument("A model draft revision requires non-empty source references");
    }
  }

  const revisionId = generateSnowflake();
  const now = new Date();

  const [inserted] = await db
    .insert(canvasRevisions)
    .values({
      id: revisionId,
      workspaceId: wsId,
      canvasId,
      parentRevisionId: params.parentRevisionId ? BigInt(params.parentRevisionId) : null,
      content: params.content,
      status: "DRAFT",
      origin: params.origin,
      sourceRefs: params.sourceRefs ? (params.sourceRefs as any) : [],
      createdByMemberId: ctx.memberId ? BigInt(ctx.memberId) : null,
      createdAt: now,
    })
    .returning();

  return mvpItem(mapRevision(inserted), [{ kind: "company_db", ref: "strategy.canvas_revisions" }]);
}

export async function getRevisionService(ctx: TenantContext, idStr: string): Promise<MvpSuccess<CanvasRevision>> {
  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(idStr);

  const [row] = await db
    .select()
    .from(canvasRevisions)
    .where(and(eq(canvasRevisions.id, id), eq(canvasRevisions.workspaceId, wsId)));

  if (!row) {
    throw APIError.notFound("Canvas revision not found");
  }

  return mvpItem(mapRevision(row), [{ kind: "company_db", ref: "strategy.canvas_revisions" }]);
}

export async function submitRevisionForReviewService(
  ctx: TenantContext,
  idStr: string
): Promise<MvpSuccess<CanvasRevision>> {
  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(idStr);

  const [row] = await db
    .select()
    .from(canvasRevisions)
    .where(and(eq(canvasRevisions.id, id), eq(canvasRevisions.workspaceId, wsId)));

  if (!row) {
    throw APIError.notFound("Canvas revision not found");
  }

  if (row.status !== "DRAFT") {
    throw APIError.failedPrecondition(`Cannot submit revision for review from status ${row.status}`);
  }

  const [updated] = await db
    .update(canvasRevisions)
    .set({ status: "IN_REVIEW" })
    .where(and(eq(canvasRevisions.id, id), eq(canvasRevisions.workspaceId, wsId)))
    .returning();

  return mvpItem(mapRevision(updated), [{ kind: "company_db", ref: "strategy.canvas_revisions" }]);
}

export async function approveRevisionService(
  ctx: TenantContext,
  idStr: string,
  reviewNote?: string | null
): Promise<MvpSuccess<CanvasRevision>> {
  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(idStr);

  const [row] = await db
    .select()
    .from(canvasRevisions)
    .where(and(eq(canvasRevisions.id, id), eq(canvasRevisions.workspaceId, wsId)));

  if (!row) {
    throw APIError.notFound("Canvas revision not found");
  }

  if (row.status !== "IN_REVIEW" && row.status !== "DRAFT") {
    throw APIError.failedPrecondition(`Cannot approve revision in status ${row.status}`);
  }

  const now = new Date();
  const [updated] = await db
    .update(canvasRevisions)
    .set({
      status: "APPROVED",
      reviewedByMemberId: ctx.memberId ? BigInt(ctx.memberId) : null,
      reviewNote: reviewNote || null,
      reviewedAt: now,
    })
    .where(and(eq(canvasRevisions.id, id), eq(canvasRevisions.workspaceId, wsId)))
    .returning();

  // Update canvas currentRevisionId to the approved revision
  await db
    .update(canvases)
    .set({
      currentRevisionId: id,
      updatedAt: now,
    })
    .where(and(eq(canvases.id, row.canvasId), eq(canvases.workspaceId, wsId)));

  return mvpItem(mapRevision(updated), [{ kind: "company_db", ref: "strategy.canvas_revisions" }]);
}

export async function rejectRevisionService(
  ctx: TenantContext,
  idStr: string,
  reviewNote?: string | null
): Promise<MvpSuccess<CanvasRevision>> {
  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(idStr);

  const [row] = await db
    .select()
    .from(canvasRevisions)
    .where(and(eq(canvasRevisions.id, id), eq(canvasRevisions.workspaceId, wsId)));

  if (!row) {
    throw APIError.notFound("Canvas revision not found");
  }

  if (row.status !== "IN_REVIEW" && row.status !== "DRAFT") {
    throw APIError.failedPrecondition(`Cannot reject revision in status ${row.status}`);
  }

  const now = new Date();
  const [updated] = await db
    .update(canvasRevisions)
    .set({
      status: "REJECTED",
      reviewedByMemberId: ctx.memberId ? BigInt(ctx.memberId) : null,
      reviewNote: reviewNote || null,
      reviewedAt: now,
    })
    .where(and(eq(canvasRevisions.id, id), eq(canvasRevisions.workspaceId, wsId)))
    .returning();

  return mvpItem(mapRevision(updated), [{ kind: "company_db", ref: "strategy.canvas_revisions" }]);
}
