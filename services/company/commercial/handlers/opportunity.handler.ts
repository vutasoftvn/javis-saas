import { api, Header } from "encore.dev/api";
import {
  SalesOpportunity,
  CreateSalesOpportunityParams as BaseCreateSalesOpportunityParams,
  createSalesOpportunityService,
  getSalesOpportunityService,
  updateOpportunityStageService,
} from "../services/opportunity.service";

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
  async ({ id, authorization }: { id: string; authorization?: Header<"Authorization"> }): Promise<SalesOpportunity> => {
    return getSalesOpportunityService(id, authorization);
  }
);

export const updateOpportunityStage = api(
  { method: "POST", path: "/commercial/opportunities/:id/stage", expose: true },
  async ({
    id,
    stage,
    authorization,
  }: {
    id: string;
    stage: string;
    authorization?: Header<"Authorization">;
  }): Promise<SalesOpportunity> => {
    return updateOpportunityStageService(id, stage, authorization);
  }
);
