import { describe, expect, it } from "vitest";
import { CanvasQuery } from "../application/canvas/canvas-query";
import { CanvasCommand } from "../application/canvas/canvas-command";
import { DrizzleCanvasRepository } from "../infrastructure/canvas/drizzle-canvas.repository";
import { CanvasDomainModel, CanvasRevisionDomainModel } from "../domain/canvas";

class FakeCanvasRepository extends DrizzleCanvasRepository {
  private canvases: CanvasDomainModel[] = [];
  private revisions: CanvasRevisionDomainModel[] = [];

  override async listCanvases(workspaceId: string): Promise<readonly CanvasDomainModel[]> {
    return this.canvases.filter((c) => c.workspaceId === workspaceId);
  }

  override async getCanvas(workspaceId: string, id: string): Promise<CanvasDomainModel | null> {
    return this.canvases.find((c) => c.workspaceId === workspaceId && c.id === id) || null;
  }

  override async createCanvas(input: any): Promise<CanvasDomainModel> {
    const c: CanvasDomainModel = {
      id: `canvas_${Date.now()}`,
      workspaceId: input.workspaceId,
      name: input.name,
      description: input.description || null,
      currentRevisionId: null,
      createdByMemberId: input.actorMemberId || null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    this.canvases.push(c);
    return c;
  }

  override async updateCanvas(input: any): Promise<CanvasDomainModel | null> {
    const idx = this.canvases.findIndex((c) => c.workspaceId === input.workspaceId && c.id === input.canvasId);
    if (idx === -1) return null;
    const existing = this.canvases[idx];
    const updated = {
      ...existing,
      name: input.name ?? existing.name,
      description: input.description !== undefined ? input.description : existing.description,
      updatedAt: new Date().toISOString(),
    };
    this.canvases[idx] = updated;
    return updated;
  }

  override async deleteCanvas(workspaceId: string, id: string): Promise<boolean> {
    const idx = this.canvases.findIndex((c) => c.workspaceId === workspaceId && c.id === id);
    if (idx === -1) return false;
    this.canvases.splice(idx, 1);
    return true;
  }

  override async createRevision(input: any): Promise<CanvasRevisionDomainModel> {
    const rev: CanvasRevisionDomainModel = {
      id: `rev_${Date.now()}`,
      workspaceId: input.workspaceId,
      canvasId: input.canvasId,
      parentRevisionId: input.parentRevisionId || null,
      content: input.content,
      status: "DRAFT",
      origin: input.origin,
      sourceRefs: input.sourceRefs || [],
      createdByMemberId: input.actorMemberId || null,
      reviewedByMemberId: null,
      reviewNote: null,
      createdAt: new Date().toISOString(),
      reviewedAt: null,
    };
    this.revisions.push(rev);
    return rev;
  }

  override async getRevision(workspaceId: string, revisionId: string): Promise<CanvasRevisionDomainModel | null> {
    return this.revisions.find((r) => r.workspaceId === workspaceId && r.id === revisionId) || null;
  }

  override async updateRevisionStatus(
    workspaceId: string,
    revisionId: string,
    status: CanvasRevisionDomainModel["status"],
    reviewerMemberId?: string | null,
    reviewNote?: string | null
  ): Promise<CanvasRevisionDomainModel | null> {
    const rev = this.revisions.find((r) => r.workspaceId === workspaceId && r.id === revisionId);
    if (!rev) return null;
    const updated = {
      ...rev,
      status,
      reviewedByMemberId: reviewerMemberId || null,
      reviewNote: reviewNote || null,
      reviewedAt: new Date().toISOString(),
    };
    const idx = this.revisions.indexOf(rev);
    this.revisions[idx] = updated;
    return updated;
  }

  override async setCanvasCurrentRevision(workspaceId: string, canvasId: string, revisionId: string): Promise<void> {
    const c = this.canvases.find((item) => item.workspaceId === workspaceId && item.id === canvasId);
    if (c) {
      (c as any).currentRevisionId = revisionId;
    }
  }
}

describe("Canvas Application Use Cases", () => {
  it("creates, queries, and updates canvas truthfully", async () => {
    const fakeRepo = new FakeCanvasRepository();
    const query = new CanvasQuery(fakeRepo);
    const command = new CanvasCommand(fakeRepo);

    const created = await command.createCanvas({
      workspaceId: "ws_101",
      actorMemberId: "mem_202",
      name: "Q3 Strategy Canvas",
      description: "Initial strategy hypothesis",
    });

    expect(created.name).toBe("Q3 Strategy Canvas");
    expect(created.workspaceId).toBe("ws_101");

    const list = await query.listCanvases("ws_101");
    expect(list).toHaveLength(1);
    expect(list[0].id).toBe(created.id);

    // Other workspace sees empty list
    const otherList = await query.listCanvases("ws_999");
    expect(otherList).toHaveLength(0);
  });

  it("handles revision lifecycle: draft -> submit review -> approve", async () => {
    const fakeRepo = new FakeCanvasRepository();
    const query = new CanvasQuery(fakeRepo);
    const command = new CanvasCommand(fakeRepo);

    const canvas = await command.createCanvas({
      workspaceId: "ws_101",
      actorMemberId: "mem_202",
      name: "BMC Model",
    });

    const rev = await command.createRevision({
      workspaceId: "ws_101",
      canvasId: canvas.id,
      actorMemberId: "mem_202",
      content: { keyPartners: ["Partner A"] },
      origin: "USER",
    });
    expect(rev.status).toBe("DRAFT");

    const submitted = await command.submitRevisionForReview("ws_101", rev.id);
    expect(submitted.status).toBe("IN_REVIEW");

    const approved = await command.approveRevision("ws_101", rev.id, "mem_admin", "Looks solid");
    expect(approved.status).toBe("APPROVED");
    expect(approved.reviewNote).toBe("Looks solid");

    const fetchedCanvas = await query.getCanvas("ws_101", canvas.id);
    expect(fetchedCanvas?.currentRevisionId).toBe(rev.id);
  });
});
