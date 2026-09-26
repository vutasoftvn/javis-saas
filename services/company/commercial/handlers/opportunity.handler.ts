import { api, Header, Query } from "encore.dev/api";
import {
  SalesOpportunity,
  CreateSalesOpportunityParams as BaseCreateSalesOpportunityParams,
  createSalesOpportunityService,
  getSalesOpportunityService,
  updateOpportunityStageService,
  listSalesOpportunitiesService,
} from "../services/opportunity.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export { SalesOpportunity };

export interface CreateSalesOpportunityParams extends BaseCreateSalesOpportunityParams {
  authorization?: Header<"Authorization">;
}

export const createSalesOpportunity = api(
  { method: "POST", path: "/commercial/opportunities", expose: true },
  async (params: CreateSalesOpportunityParams): Promise<SalesOpportunity> => {
    return createSalesOpportunityService(params, params.authorization);
  }
);

export const getSalesOpportunity = api(
  { method: "GET", path: "/commercial/opportunities/:id", expose: true },
  async ({
    id,
    workspaceId,
    authorization,
  }: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<SalesOpportunity> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getSalesOpportunityService(id, ctx);
  }
);

export const updateOpportunityStage = api(
  { method: "POST", path: "/commercial/opportunities/:id/stage", expose: true },
  async ({
    id,
    stage,
    workspaceId,
    authorization,
  }: {
    id: string;
    stage: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<SalesOpportunity> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return updateOpportunityStageService(id, stage, ctx);
  }
);

// Dashboard CRM — pipeline cơ hội bán hàng, lọc tuỳ chọn theo stage/account.
export const listSalesOpportunities = api(
  { method: "GET", path: "/commercial/workspaces/:workspaceId/opportunities", expose: true },
  async (params: {
    workspaceId: string;
    stage?: Query<string>;
    accountId?: Query<string>;
    authorization?: Header<"Authorization">;
  }): Promise<{ opportunities: SalesOpportunity[] }> => {
    const opportunities = await listSalesOpportunitiesService(params.workspaceId, params.authorization, {
      stage: params.stage,
      accountId: params.accountId,
    });
    return { opportunities };
  }
);
