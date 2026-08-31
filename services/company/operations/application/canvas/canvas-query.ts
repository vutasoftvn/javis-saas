import { CanvasDomainModel, CanvasRevisionDomainModel } from "../../domain/canvas";
import { DrizzleCanvasRepository } from "../../infrastructure/canvas/drizzle-canvas.repository";

export class CanvasQuery {
  constructor(private readonly repo: DrizzleCanvasRepository = new DrizzleCanvasRepository()) {}

  async listCanvases(workspaceId: string): Promise<readonly CanvasDomainModel[]> {
    return this.repo.listCanvases(workspaceId);
  }

  async getCanvas(workspaceId: string, id: string): Promise<CanvasDomainModel | null> {
    return this.repo.getCanvas(workspaceId, id);
  }

  async getRevision(workspaceId: string, revisionId: string): Promise<CanvasRevisionDomainModel | null> {
    return this.repo.getRevision(workspaceId, revisionId);
  }
}
