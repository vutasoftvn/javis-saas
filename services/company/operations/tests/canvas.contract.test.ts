import { describe, expect, it } from "vitest";
import { CanvasQuery } from "../application/canvas/canvas-query";
import { CanvasCommand } from "../application/canvas/canvas-command";
import { DrizzleCanvasRepository } from "../infrastructure/canvas/drizzle-canvas.repository";
import { CanvasDomainModel, CanvasRevisionDomainModel } from "../domain/canvas";

class StubRepo extends DrizzleCanvasRepository {
  public store: CanvasDomainModel[] = [];
  public revStore: CanvasRevisionDomainModel[] = [];

  override async listCanvases(workspaceId: string): Promise<readonly CanvasDomainModel[]> {
    return this.store.filter((x) => x.workspaceId === workspaceId);
  }

  override async getCanvas(workspaceId: string, id: string): Promise<CanvasDomainModel | null> {
    return this.store.find((x) => x.workspaceId === workspaceId && x.id === id) || null;
  }

  override async createCanvas(input: any): Promise<CanvasDomainModel> {
    const item: CanvasDomainModel = {
      id: "90001",
      workspaceId: input.workspaceId,
      name: input.name,
      description: input.description || null,
      currentRevisionId: null,
      createdByMemberId: input.actorMemberId || null,
      createdAt: "2026-08-31T12:00:00.000Z",
      updatedAt: "2026-08-31T12:00:00.000Z",
    };
    this.store.push(item);
    return item;
  }
}

describe("Canvas Contract Tests", () => {
  it("enforces required fields and string IDs on CanvasReadModel", async () => {
    const stub = new StubRepo();
    const query = new CanvasQuery(stub);
    const cmd = new CanvasCommand(stub);

    const created = await cmd.createCanvas({
      workspaceId: "ws_canvas_contract",
      actorMemberId: "mem_contract",
      name: "Lean Canvas MVP",
      description: "Validated hypothesis",
    });

    expect(typeof created.id).toBe("string");
    expect(typeof created.workspaceId).toBe("string");
    expect(created.name).toBe("Lean Canvas MVP");
    expect(created.description).toBe("Validated hypothesis");
    expect(typeof created.createdAt).toBe("string");
    expect(typeof created.updatedAt).toBe("string");

    const fetched = await query.getCanvas("ws_canvas_contract", created.id);
    expect(fetched).not.toBeNull();
    expect(fetched?.id).toBe(created.id);
  });

  it("rejects empty canvas name with explicit validation error", async () => {
    const stub = new StubRepo();
    const cmd = new CanvasCommand(stub);

    await expect(
      cmd.createCanvas({
        workspaceId: "ws_canvas_contract",
        actorMemberId: "mem_contract",
        name: "   ",
      })
    ).rejects.toThrow("Canvas name cannot be empty");
  });
});
