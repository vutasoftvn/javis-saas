import { describe, expect, it } from "vitest";
import { CanvasQuery } from "../application/canvas/canvas-query";
import { CanvasCommand } from "../application/canvas/canvas-command";
import { DrizzleCanvasRepository } from "../infrastructure/canvas/drizzle-canvas.repository";
import { CanvasDomainModel } from "../domain/canvas";

class IsolatedRepo extends DrizzleCanvasRepository {
  public store: CanvasDomainModel[] = [];

  override async listCanvases(workspaceId: string): Promise<readonly CanvasDomainModel[]> {
    return this.store.filter((x) => x.workspaceId === workspaceId);
  }

  override async getCanvas(workspaceId: string, id: string): Promise<CanvasDomainModel | null> {
    return this.store.find((x) => x.workspaceId === workspaceId && x.id === id) || null;
  }

  override async createCanvas(input: any): Promise<CanvasDomainModel> {
    const item: CanvasDomainModel = {
      id: `id_${Date.now()}_${Math.random()}`,
      workspaceId: input.workspaceId,
      name: input.name,
      description: input.description || null,
      currentRevisionId: null,
      createdByMemberId: input.actorMemberId || null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    this.store.push(item);
    return item;
  }
}

describe("Canvas Tenant Isolation Tests", () => {
  it("strictly scopes canvas access by workspace ID", async () => {
    const repo = new IsolatedRepo();
    const query = new CanvasQuery(repo);
    const cmd = new CanvasCommand(repo);

    const ws1Canvas = await cmd.createCanvas({
      workspaceId: "ws_alpha",
      actorMemberId: "mem_1",
      name: "Alpha Canvas",
    });

    const ws2Canvas = await cmd.createCanvas({
      workspaceId: "ws_beta",
      actorMemberId: "mem_2",
      name: "Beta Canvas",
    });

    // Workspace Alpha only sees Alpha canvas
    const listAlpha = await query.listCanvases("ws_alpha");
    expect(listAlpha).toHaveLength(1);
    expect(listAlpha[0].id).toBe(ws1Canvas.id);

    // Workspace Beta only sees Beta canvas
    const listBeta = await query.listCanvases("ws_beta");
    expect(listBeta).toHaveLength(1);
    expect(listBeta[0].id).toBe(ws2Canvas.id);

    // Workspace Alpha cannot fetch Beta canvas directly
    const crossTenantGet = await query.getCanvas("ws_alpha", ws2Canvas.id);
    expect(crossTenantGet).toBeNull();
  });
});
