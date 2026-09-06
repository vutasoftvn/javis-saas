import { api, APIError, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  listCycleReviewsService,
  getCycleReviewService,
  startCycleReviewService,
  updateCycleReviewService,
  createCustomMidCycleReviewService,
  closeCycleReviewService,
  CycleReviewView,
} from "../services/cycle-review.service";

export interface ListCycleReviewsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  cycleId: string;
}

export interface ListCycleReviewsResponse {
  reviews: CycleReviewView[];
}

export const listCycleReviews = api(
  { method: "GET", path: "/operations/cycles/:cycleId/reviews", expose: true },
  async (params: ListCycleReviewsParams): Promise<ListCycleReviewsResponse> => {
    if (!params.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const reviews = await listCycleReviewsService(BigInt(ctx.workspaceId), BigInt(params.cycleId));
    return { reviews };
  }
);

export interface GetCycleReviewParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export const getCycleReview = api(
  { method: "GET", path: "/operations/cycle-reviews/:id", expose: true },
  async (params: GetCycleReviewParams): Promise<CycleReviewView> => {
    if (!params.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getCycleReviewService(BigInt(ctx.workspaceId), BigInt(params.id));
  }
);

export interface StartCycleReviewParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
}

export const startCycleReview = api(
  { method: "POST", path: "/operations/cycle-reviews/:id/start", expose: true },
  async (params: StartCycleReviewParams): Promise<CycleReviewView> => {
    if (!params.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return startCycleReviewService(ctx, BigInt(params.id));
  }
);

export interface UpdateCycleReviewParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  conclusion?: string;
}

export const updateCycleReview = api(
  { method: "PATCH", path: "/operations/cycle-reviews/:id", expose: true },
  async (params: UpdateCycleReviewParams): Promise<CycleReviewView> => {
    if (!params.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return updateCycleReviewService(ctx, BigInt(params.id), {
      conclusion: params.conclusion,
    });
  }
);

export interface CreateCustomMidCycleReviewParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  cycleId: string;
  scheduledWeekNo: number;
}

export const createCustomMidCycleReview = api(
  { method: "POST", path: "/operations/cycles/:cycleId/reviews/custom-mid-cycle", expose: true },
  async (params: CreateCustomMidCycleReviewParams): Promise<CycleReviewView> => {
    if (!params.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createCustomMidCycleReviewService(ctx, BigInt(params.cycleId), params.scheduledWeekNo);
  }
);

export interface CloseCycleReviewParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  conclusion?: string;
  decisionId?: string;
}

export const closeCycleReview = api(
  { method: "POST", path: "/operations/cycle-reviews/:id/close", expose: true },
  async (params: CloseCycleReviewParams): Promise<CycleReviewView> => {
    if (!params.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return closeCycleReviewService(ctx, BigInt(params.id), {
      conclusion: params.conclusion,
      decisionId: params.decisionId,
    });
  }
);
