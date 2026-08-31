import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { MvpSuccess, mvpList } from "../../shared/contracts/mvp-response";
import {
  Canvas,
  CanvasRevision,
  listCanvasesService,
  createCanvasService,
  getCanvasService,
  updateCanvasService,
  deleteCanvasService,
  createRevisionService,
  getRevisionService,
  submitRevisionForReviewService,
  approveRevisionService,
  rejectRevisionService,
} from "../services/canvas.service";

export interface CanvasAuthParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export interface CreateCanvasParams extends CanvasAuthParams {
  name: string;
  description?: string | null;
}

export interface CanvasIdParams extends CanvasAuthParams {
  id: string;
}

export interface UpdateCanvasParams extends CanvasIdParams {
  name?: string;
  description?: string | null;
}

export interface CreateRevisionParams extends CanvasIdParams {
  content: Record<string, unknown>;
  origin: "USER" | "MODEL_DRAFT";
  sourceRefs?: any[];
  parentRevisionId?: string | null;
}

export interface RevisionReviewParams extends CanvasIdParams {
  reviewNote?: string | null;
}

// ─── Strategy Canvases Handlers ───

export const listCanvases = api(
  { expose: true, method: "GET", path: "/operations/strategy/canvases" },
  async (params: CanvasAuthParams): Promise<MvpSuccess<readonly Canvas[]>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listCanvasesService(ctx);
  }
);

export const createCanvas = api(
  { expose: true, method: "POST", path: "/operations/strategy/canvases" },
  async (params: CreateCanvasParams): Promise<MvpSuccess<Canvas>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createCanvasService(ctx, {
      name: params.name,
      description: params.description,
    });
  }
);

export const getCanvas = api(
  { expose: true, method: "GET", path: "/operations/strategy/canvases/:id" },
  async (params: CanvasIdParams): Promise<MvpSuccess<Canvas>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getCanvasService(ctx, params.id);
  }
);

export const updateCanvas = api(
  { expose: true, method: "PUT", path: "/operations/strategy/canvases/:id" },
  async (params: UpdateCanvasParams): Promise<MvpSuccess<Canvas>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return updateCanvasService(ctx, params.id, {
      name: params.name,
      description: params.description,
    });
  }
);

export const deleteCanvas = api(
  { expose: true, method: "DELETE", path: "/operations/strategy/canvases/:id" },
  async (params: CanvasIdParams): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    await deleteCanvasService(ctx, params.id);
    return { success: true };
  }
);

export const createRevision = api(
  { expose: true, method: "POST", path: "/operations/strategy/canvases/:id/revisions" },
  async (params: CreateRevisionParams): Promise<MvpSuccess<CanvasRevision>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createRevisionService(ctx, params.id, {
      content: params.content,
      origin: params.origin,
      sourceRefs: params.sourceRefs,
      parentRevisionId: params.parentRevisionId,
    });
  }
);

export const getRevision = api(
  { expose: true, method: "GET", path: "/operations/strategy/canvas-revisions/:id" },
  async (params: CanvasIdParams): Promise<MvpSuccess<CanvasRevision>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getRevisionService(ctx, params.id);
  }
);

export const submitRevisionForReview = api(
  { expose: true, method: "POST", path: "/operations/strategy/canvas-revisions/:id/submit-review" },
  async (params: CanvasIdParams): Promise<MvpSuccess<CanvasRevision>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return submitRevisionForReviewService(ctx, params.id);
  }
);

export const approveRevision = api(
  { expose: true, method: "POST", path: "/operations/strategy/canvas-revisions/:id/approve" },
  async (params: RevisionReviewParams): Promise<MvpSuccess<CanvasRevision>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return approveRevisionService(ctx, params.id, params.reviewNote);
  }
);

export const rejectRevision = api(
  { expose: true, method: "POST", path: "/operations/strategy/canvas-revisions/:id/reject" },
  async (params: RevisionReviewParams): Promise<MvpSuccess<CanvasRevision>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return rejectRevisionService(ctx, params.id, params.reviewNote);
  }
);

export const getFundingMatches = api(
  { expose: true, method: "GET", path: "/operations/strategy/funding-matches" },
  async (params: CanvasAuthParams): Promise<MvpSuccess<readonly any[]>> => {
    await requireWorkspaceAccess(params.authorization, params.workspaceId);
    // Funding catalog has no fake seed; returns genuine empty list from connector
    return mvpList([], [{ kind: "external_connector", ref: "funding.provider" }]);
  }
);
