export interface CanvasSummary {
  readonly id: string;
  readonly workspaceId: string;
  readonly name: string;
  readonly description: string | null;
  readonly currentRevisionId: string | null;
  readonly createdByMemberId: string | null;
  readonly createdAt: Date;
  readonly updatedAt: Date;
}

export interface CanvasPort {
  list(workspaceId: string): Promise<readonly CanvasSummary[]>;
  get(workspaceId: string, id: string): Promise<CanvasSummary | null>;
  create(params: {
    workspaceId: string;
    name: string;
    description?: string | null;
    createdByMemberId?: string | null;
  }): Promise<CanvasSummary>;
  update(
    workspaceId: string,
    id: string,
    params: { name?: string; description?: string | null }
  ): Promise<CanvasSummary | null>;
  delete(workspaceId: string, id: string): Promise<boolean>;
}
