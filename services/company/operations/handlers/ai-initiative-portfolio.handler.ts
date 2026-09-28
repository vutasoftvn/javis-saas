import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getAiInitiativePortfolio as getAiInitiativePortfolioService,
  AiInitiativePortfolioResponse,
} from "../services/ai-initiative-portfolio.service";

export interface GetAiInitiativePortfolioParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
}

export const getAiInitiativePortfolio = api(
  {
    expose: true,
    method: "GET",
    path: "/operations/projects/:projectId/ai-initiatives/portfolio",
  },
  async (params: GetAiInitiativePortfolioParams): Promise<AiInitiativePortfolioResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getAiInitiativePortfolioService(ctx, params.projectId);
  }
);
