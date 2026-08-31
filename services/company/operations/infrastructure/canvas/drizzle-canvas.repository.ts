import { and, eq, isNull, desc } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import {
  CanvasDomainModel,
  CanvasRevisionDomainModel,
  CreateCanvasInput,
  UpdateCanvasInput,
  CreateRevisionInput,
} from "../../domain/canvas";

const { canvases, canvasRevisions } = schema;

function mapCanvas(row: typeof canvases.$inferSelect): CanvasDomainModel {
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

function mapRevision(row: typeof canvasRevisions.$inferSelect): CanvasRevisionDomainModel {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    canvasId: row.canvasId.toString(),
    parentRevisionId: row.parentRevisionId ? row.parentRevisionId.toString() : null,
    content: (row.content || {}) as Record<string, unknown>,
    status: row.status as CanvasRevisionDomainModel["status"],
    origin: row.origin as CanvasRevisionDomainModel["origin"],
    sourceRefs: (row.sourceRefs || []) as unknown as readonly { kind: string; ref: string; observedAt?: string }[],
    createdByMemberId: row.createdByMemberId ? row.createdByMemberId.toString() : null,
    reviewedByMemberId: row.reviewedByMemberId ? row.reviewedByMemberId.toString() : null,
    reviewNote: row.reviewNote,
    createdAt: row.createdAt.toISOString(),
    reviewedAt: row.reviewedAt ? row.reviewedAt.toISOString() : null,
  };
}

export class DrizzleCanvasRepository {
  async listCanvases(workspaceId: string): Promise<readonly CanvasDomainModel[]> {
    const wsId = BigInt(workspaceId);
    const rows = await db
      .select()
      .from(canvases)
      .where(and(eq(canvases.workspaceId, wsId), isNull(canvases.deletedAt)))
      .orderBy(desc(canvases.updatedAt));

    return rows.map(mapCanvas);
  }

  async getCanvas(workspaceId: string, id: string): Promise<CanvasDomainModel | null> {
    const wsId = BigInt(workspaceId);
    const cId = BigInt(id);

    const [row] = await db
      .select()
      .from(canvases)
      .where(and(eq(canvases.id, cId), eq(canvases.workspaceId, wsId), isNull(canvases.deletedAt)));

    return row ? mapCanvas(row) : null;
  }

  async createCanvas(input: CreateCanvasInput): Promise<CanvasDomainModel> {
    const wsId = BigInt(input.workspaceId);
    const id = generateSnowflake();
    const now = new Date();

    const [inserted] = await db
      .insert(canvases)
      .values({
        id,
        workspaceId: wsId,
        name: input.name.trim(),
        description: input.description || null,
        createdByMemberId: input.actorMemberId ? BigInt(input.actorMemberId) : null,
        createdAt: now,
        updatedAt: now,
      })
      .returning();

    return mapCanvas(inserted);
  }

  async updateCanvas(input: UpdateCanvasInput): Promise<CanvasDomainModel | null> {
    const wsId = BigInt(input.workspaceId);
    const cId = BigInt(input.canvasId);

    const updates: Partial<typeof canvases.$inferInsert> = {
      updatedAt: new Date(),
    };
    if (input.name !== undefined) {
      updates.name = input.name.trim();
    }
    if (input.description !== undefined) {
      updates.description = input.description;
    }

    const [updated] = await db
      .update(canvases)
      .set(updates)
      .where(and(eq(canvases.id, cId), eq(canvases.workspaceId, wsId), isNull(canvases.deletedAt)))
      .returning();

    return updated ? mapCanvas(updated) : null;
  }

  async deleteCanvas(workspaceId: string, id: string): Promise<boolean> {
    const wsId = BigInt(workspaceId);
    const cId = BigInt(id);

    const [updated] = await db
      .update(canvases)
      .set({ deletedAt: new Date() })
      .where(and(eq(canvases.id, cId), eq(canvases.workspaceId, wsId), isNull(canvases.deletedAt)))
      .returning();

    return !!updated;
  }

  async createRevision(input: CreateRevisionInput): Promise<CanvasRevisionDomainModel> {
    const wsId = BigInt(input.workspaceId);
    const canvasId = BigInt(input.canvasId);
    const revisionId = generateSnowflake();
    const now = new Date();

    const [inserted] = await db
      .insert(canvasRevisions)
      .values({
        id: revisionId,
        workspaceId: wsId,
        canvasId,
        parentRevisionId: input.parentRevisionId ? BigInt(input.parentRevisionId) : null,
        content: input.content,
        status: "DRAFT",
        origin: input.origin,
        sourceRefs: (input.sourceRefs || []) as any,
        createdByMemberId: input.actorMemberId ? BigInt(input.actorMemberId) : null,
        createdAt: now,
      })
      .returning();

    return mapRevision(inserted);
  }

  async getRevision(workspaceId: string, revisionId: string): Promise<CanvasRevisionDomainModel | null> {
    const wsId = BigInt(workspaceId);
    const rId = BigInt(revisionId);

    const [row] = await db
      .select()
      .from(canvasRevisions)
      .where(and(eq(canvasRevisions.id, rId), eq(canvasRevisions.workspaceId, wsId)));

    return row ? mapRevision(row) : null;
  }

  async updateRevisionStatus(
    workspaceId: string,
    revisionId: string,
    status: CanvasRevisionDomainModel["status"],
    reviewerMemberId?: string | null,
    reviewNote?: string | null
  ): Promise<CanvasRevisionDomainModel | null> {
    const wsId = BigInt(workspaceId);
    const rId = BigInt(revisionId);
    const now = new Date();

    const [updated] = await db
      .update(canvasRevisions)
      .set({
        status,
        reviewedByMemberId: reviewerMemberId ? BigInt(reviewerMemberId) : null,
        reviewNote: reviewNote || null,
        reviewedAt: status === "APPROVED" || status === "REJECTED" ? now : null,
      })
      .where(and(eq(canvasRevisions.id, rId), eq(canvasRevisions.workspaceId, wsId)))
      .returning();

    return updated ? mapRevision(updated) : null;
  }

  async setCanvasCurrentRevision(workspaceId: string, canvasId: string, revisionId: string): Promise<void> {
    const wsId = BigInt(workspaceId);
    const cId = BigInt(canvasId);
    const rId = BigInt(revisionId);

    await db
      .update(canvases)
      .set({ currentRevisionId: rId, updatedAt: new Date() })
      .where(and(eq(canvases.id, cId), eq(canvases.workspaceId, wsId)));
  }
}
