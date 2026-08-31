import {
  CanvasDomainModel,
  CanvasRevisionDomainModel,
  CreateCanvasInput,
  UpdateCanvasInput,
  CreateRevisionInput,
} from "../../domain/canvas";
import { DrizzleCanvasRepository } from "../../infrastructure/canvas/drizzle-canvas.repository";

export class CanvasCommand {
  constructor(private readonly repo: DrizzleCanvasRepository = new DrizzleCanvasRepository()) {}

  async createCanvas(input: CreateCanvasInput): Promise<CanvasDomainModel> {
    if (!input.name || input.name.trim().length === 0) {
      throw new Error("Canvas name cannot be empty");
    }
    return this.repo.createCanvas(input);
  }

  async updateCanvas(input: UpdateCanvasInput): Promise<CanvasDomainModel | null> {
    if (input.name !== undefined && input.name.trim().length === 0) {
      throw new Error("Canvas name cannot be empty");
    }
    return this.repo.updateCanvas(input);
  }

  async deleteCanvas(workspaceId: string, id: string): Promise<boolean> {
    return this.repo.deleteCanvas(workspaceId, id);
  }

  async createRevision(input: CreateRevisionInput): Promise<CanvasRevisionDomainModel> {
    const canvas = await this.repo.getCanvas(input.workspaceId, input.canvasId);
    if (!canvas) {
      throw new Error("Canvas not found");
    }

    if (input.origin === "MODEL_DRAFT") {
      if (!input.sourceRefs || input.sourceRefs.length === 0) {
        throw new Error("A model draft revision requires non-empty source references");
      }
    }

    return this.repo.createRevision(input);
  }

  async submitRevisionForReview(workspaceId: string, revisionId: string): Promise<CanvasRevisionDomainModel> {
    const revision = await this.repo.getRevision(workspaceId, revisionId);
    if (!revision) {
      throw new Error("Canvas revision not found");
    }
    if (revision.status !== "DRAFT") {
      throw new Error(`Cannot submit revision for review from status ${revision.status}`);
    }

    const updated = await this.repo.updateRevisionStatus(workspaceId, revisionId, "IN_REVIEW");
    if (!updated) throw new Error("Failed to update revision status");
    return updated;
  }

  async approveRevision(
    workspaceId: string,
    revisionId: string,
    reviewerMemberId?: string | null,
    reviewNote?: string | null
  ): Promise<CanvasRevisionDomainModel> {
    const revision = await this.repo.getRevision(workspaceId, revisionId);
    if (!revision) {
      throw new Error("Canvas revision not found");
    }
    if (revision.status !== "IN_REVIEW" && revision.status !== "DRAFT") {
      throw new Error(`Cannot approve revision in status ${revision.status}`);
    }

    const updated = await this.repo.updateRevisionStatus(
      workspaceId,
      revisionId,
      "APPROVED",
      reviewerMemberId,
      reviewNote
    );
    if (!updated) throw new Error("Failed to approve revision");

    await this.repo.setCanvasCurrentRevision(workspaceId, revision.canvasId, revisionId);
    return updated;
  }

  async rejectRevision(
    workspaceId: string,
    revisionId: string,
    reviewerMemberId?: string | null,
    reviewNote?: string | null
  ): Promise<CanvasRevisionDomainModel> {
    const revision = await this.repo.getRevision(workspaceId, revisionId);
    if (!revision) {
      throw new Error("Canvas revision not found");
    }
    if (revision.status !== "IN_REVIEW" && revision.status !== "DRAFT") {
      throw new Error(`Cannot reject revision in status ${revision.status}`);
    }

    const updated = await this.repo.updateRevisionStatus(
      workspaceId,
      revisionId,
      "REJECTED",
      reviewerMemberId,
      reviewNote
    );
    if (!updated) throw new Error("Failed to reject revision");
    return updated;
  }
}
