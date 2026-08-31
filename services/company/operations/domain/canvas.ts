export interface CanvasDomainModel {
  readonly id: string;
  readonly workspaceId: string;
  readonly name: string;
  readonly description: string | null;
  readonly currentRevisionId: string | null;
  readonly createdByMemberId: string | null;
  readonly createdAt: string;
  readonly updatedAt: string;
}

export interface CanvasRevisionDomainModel {
  readonly id: string;
  readonly workspaceId: string;
  readonly canvasId: string;
  readonly parentRevisionId: string | null;
  readonly content: Record<string, unknown>;
  readonly status: "DRAFT" | "IN_REVIEW" | "APPROVED" | "REJECTED";
  readonly origin: "USER" | "MODEL_DRAFT";
  readonly sourceRefs: readonly { kind: string; ref: string; observedAt?: string }[];
  readonly createdByMemberId: string | null;
  readonly reviewedByMemberId: string | null;
  readonly reviewNote: string | null;
  readonly createdAt: string;
  readonly reviewedAt: string | null;
}

export interface CreateCanvasInput {
  readonly workspaceId: string;
  readonly actorMemberId: string | null;
  readonly name: string;
  readonly description?: string | null;
}

export interface UpdateCanvasInput {
  readonly workspaceId: string;
  readonly canvasId: string;
  readonly name?: string;
  readonly description?: string | null;
}

export interface CreateRevisionInput {
  readonly workspaceId: string;
  readonly canvasId: string;
  readonly actorMemberId: string | null;
  readonly parentRevisionId?: string | null;
  readonly content: Record<string, unknown>;
  readonly origin: "USER" | "MODEL_DRAFT";
  readonly sourceRefs?: readonly { kind: string; ref: string; observedAt?: string }[];
}
