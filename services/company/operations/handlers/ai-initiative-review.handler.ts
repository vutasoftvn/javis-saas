import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  recordAiInitiativeReview as recordAiInitiativeReviewService,
  pauseAiInitiative as pauseAiInitiativeService,
  AiInitiativeReviewSummary,
  PauseAiInitiativeResult,
} from "../services/ai-initiative-review.service";

export interface RecordReviewApiParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  initiativeId: string;
  reviewCadenceDays?: number;
  findings: string;
  recommendation: "CONTINUE" | "PAUSE" | "REVISE_BUDGET" | "REVISE_METRIC" | "SCALE_UP" | "RETIRE";
}

export interface PauseInitiativeApiParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  initiativeId: string;
  reasonCode: string;
  reason?: string;
}

export const recordAiInitiativeReview = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/ai-initiatives/:initiativeId/reviews",
  },
  async (params: RecordReviewApiParams): Promise<AiInitiativeReviewSummary> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return recordAiInitiativeReviewService(ctx, params);
  }
);

export const pauseAiInitiative = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/ai-initiatives/:initiativeId/pause",
  },
  async (params: PauseInitiativeApiParams): Promise<PauseAiInitiativeResult> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return pauseAiInitiativeService(ctx, params);
  }
);
