import { APIError } from "encore.dev/api";
import { TenantContext } from "../../shared/types/tenant_context";
import { mvpList, mvpItem, MvpSuccess, MvpSourceRef } from "../../shared/contracts/mvp-response";
import { CanvasDomainModel, CanvasRevisionDomainModel } from "../domain/canvas";
import { CanvasQuery } from "../application/canvas/canvas-query";
import { CanvasCommand } from "../application/canvas/canvas-command";

export type Canvas = CanvasDomainModel;
export type CanvasRevision = CanvasRevisionDomainModel;

const query = new CanvasQuery();
const command = new CanvasCommand();

export async function listCanvasesService(ctx: TenantContext): Promise<MvpSuccess<readonly Canvas[]>> {
  const rows = await query.listCanvases(ctx.workspaceId);
  return mvpList(
    rows,
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

  const inserted = await command.createCanvas({
    workspaceId: ctx.workspaceId,
    actorMemberId: ctx.workforceMemberId || null,
    name: params.name,
    description: params.description,
  });

  return mvpItem(inserted, [{ kind: "company_db", ref: "strategy.canvases" }]);
}

export async function getCanvasService(ctx: TenantContext, idStr: string): Promise<MvpSuccess<Canvas>> {
  const row = await query.getCanvas(ctx.workspaceId, idStr);
  if (!row) {
    throw APIError.notFound("Canvas not found");
  }

  return mvpItem(row, [{ kind: "company_db", ref: "strategy.canvases" }]);
}

export async function updateCanvasService(
  ctx: TenantContext,
  idStr: string,
  params: { name?: string; description?: string | null }
): Promise<MvpSuccess<Canvas>> {
  const existing = await query.getCanvas(ctx.workspaceId, idStr);
  if (!existing) {
    throw APIError.notFound("Canvas not found");
  }

  if (params.name !== undefined && params.name.trim().length === 0) {
    throw APIError.invalidArgument("Canvas name cannot be empty");
  }

  const updated = await command.updateCanvas({
    workspaceId: ctx.workspaceId,
    canvasId: idStr,
    name: params.name,
    description: params.description,
  });

  if (!updated) {
    throw APIError.notFound("Canvas not found");
  }

  return mvpItem(updated, [{ kind: "company_db", ref: "strategy.canvases" }]);
}

export async function deleteCanvasService(ctx: TenantContext, idStr: string): Promise<void> {
  const existing = await query.getCanvas(ctx.workspaceId, idStr);
  if (!existing) {
    throw APIError.notFound("Canvas not found");
  }

  await command.deleteCanvas(ctx.workspaceId, idStr);
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
  const canvas = await query.getCanvas(ctx.workspaceId, canvasIdStr);
  if (!canvas) {
    throw APIError.notFound("Canvas not found");
  }

  if (params.origin === "MODEL_DRAFT") {
    if (!params.sourceRefs || params.sourceRefs.length === 0) {
      throw APIError.invalidArgument("A model draft revision requires non-empty source references");
    }
  }

  const inserted = await command.createRevision({
    workspaceId: ctx.workspaceId,
    canvasId: canvasIdStr,
    actorMemberId: ctx.workforceMemberId || null,
    content: params.content,
    origin: params.origin,
    sourceRefs: params.sourceRefs,
    parentRevisionId: params.parentRevisionId,
  });

  return mvpItem(inserted, [{ kind: "company_db", ref: "strategy.canvas_revisions" }]);
}

export async function getRevisionService(ctx: TenantContext, idStr: string): Promise<MvpSuccess<CanvasRevision>> {
  const row = await query.getRevision(ctx.workspaceId, idStr);
  if (!row) {
    throw APIError.notFound("Canvas revision not found");
  }

  return mvpItem(row, [{ kind: "company_db", ref: "strategy.canvas_revisions" }]);
}

export async function submitRevisionForReviewService(
  ctx: TenantContext,
  idStr: string
): Promise<MvpSuccess<CanvasRevision>> {
  const row = await query.getRevision(ctx.workspaceId, idStr);
  if (!row) {
    throw APIError.notFound("Canvas revision not found");
  }

  if (row.status !== "DRAFT") {
    throw APIError.failedPrecondition(`Cannot submit revision for review from status ${row.status}`);
  }

  try {
    const updated = await command.submitRevisionForReview(ctx.workspaceId, idStr);
    return mvpItem(updated, [{ kind: "company_db", ref: "strategy.canvas_revisions" }]);
  } catch (err: any) {
    throw APIError.failedPrecondition(err.message);
  }
}

export async function approveRevisionService(
  ctx: TenantContext,
  idStr: string,
  reviewNote?: string | null
): Promise<MvpSuccess<CanvasRevision>> {
  const row = await query.getRevision(ctx.workspaceId, idStr);
  if (!row) {
    throw APIError.notFound("Canvas revision not found");
  }

  if (row.status !== "IN_REVIEW" && row.status !== "DRAFT") {
    throw APIError.failedPrecondition(`Cannot approve revision in status ${row.status}`);
  }

  try {
    const updated = await command.approveRevision(
      ctx.workspaceId,
      idStr,
      ctx.workforceMemberId || null,
      reviewNote
    );
    return mvpItem(updated, [{ kind: "company_db", ref: "strategy.canvas_revisions" }]);
  } catch (err: any) {
    throw APIError.failedPrecondition(err.message);
  }
}

export async function rejectRevisionService(
  ctx: TenantContext,
  idStr: string,
  reviewNote?: string | null
): Promise<MvpSuccess<CanvasRevision>> {
  const row = await query.getRevision(ctx.workspaceId, idStr);
  if (!row) {
    throw APIError.notFound("Canvas revision not found");
  }

  if (row.status !== "IN_REVIEW" && row.status !== "DRAFT") {
    throw APIError.failedPrecondition(`Cannot reject revision in status ${row.status}`);
  }

  try {
    const updated = await command.rejectRevision(
      ctx.workspaceId,
      idStr,
      ctx.workforceMemberId || null,
      reviewNote
    );
    return mvpItem(updated, [{ kind: "company_db", ref: "strategy.canvas_revisions" }]);
  } catch (err: any) {
    throw APIError.failedPrecondition(err.message);
  }
}
