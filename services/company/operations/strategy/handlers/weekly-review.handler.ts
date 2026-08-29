import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  createWeeklyReviewService,
  listWeeklyReviewsService,
  completeWeeklyReviewService,
  WeeklyReviewView,
} from "../services/weekly-review.service";

export interface ListWeeklyReviewsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const getWeeklyReviews = api(
  { method: "GET", path: "/operations/strategy/weekly-reviews", expose: true },
  async (params: ListWeeklyReviewsParams): Promise<{ reviews: WeeklyReviewView[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const reviews = await listWeeklyReviewsService(BigInt(ctx.workspaceId));
    return { reviews };
  }
);

export interface CreateWeeklyReviewParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  weekStartDate: string;
  summary: string;
  stageAssessment?: string;
  cashSummary?: string;
  obligationsSummary?: string;
  actionProposals?: any[];
}

export const postWeeklyReview = api(
  { method: "POST", path: "/operations/strategy/weekly-reviews", expose: true },
  async (params: CreateWeeklyReviewParams): Promise<WeeklyReviewView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createWeeklyReviewService({
      workspaceId: BigInt(ctx.workspaceId),
      weekStartDate: params.weekStartDate,
      summary: params.summary,
      stageAssessment: params.stageAssessment,
      cashSummary: params.cashSummary,
      obligationsSummary: params.obligationsSummary,
      actionProposals: params.actionProposals,
    });
  }
);

export interface CompleteWeeklyReviewParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const postCompleteWeeklyReview = api(
  { method: "POST", path: "/operations/strategy/weekly-reviews/:id/complete", expose: true },
  async (params: CompleteWeeklyReviewParams): Promise<WeeklyReviewView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return completeWeeklyReviewService({
      reviewId: BigInt(params.id),
      completedBy: BigInt(ctx.userId || "1"),
    });
  }
);
