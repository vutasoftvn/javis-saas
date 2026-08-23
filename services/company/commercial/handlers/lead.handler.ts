import { api, Header } from "encore.dev/api";
import {
  SalesLead,
  CreateSalesLeadParams as BaseCreateSalesLeadParams,
  createSalesLeadService,
  getSalesLeadService,
  listSalesLeadsService,
  updateLeadStageService,
} from "../services/lead.service";

export { SalesLead };

export interface CreateSalesLeadParams extends BaseCreateSalesLeadParams {
  authorization?: Header<"Authorization">;
}

export const createSalesLead = api(
  { method: "POST", path: "/commercial/leads", expose: true },
  async (params: CreateSalesLeadParams): Promise<SalesLead> => {
    return createSalesLeadService(params, params.authorization);
  }
);

export const getSalesLead = api(
  { method: "GET", path: "/commercial/leads/:id", expose: true },
  async ({ id, authorization }: { id: string; authorization?: Header<"Authorization"> }): Promise<SalesLead> => {
    return getSalesLeadService(id, authorization);
  }
);

export const listSalesLeads = api(
  { method: "GET", path: "/commercial/leads", expose: true },
  async ({
    workspaceId,
    authorization,
  }: {
    workspaceId: string;
    authorization?: Header<"Authorization">;
  }): Promise<{ leads: SalesLead[] }> => {
    const leads = await listSalesLeadsService(workspaceId, authorization);
    return { leads };
  }
);

export const updateLeadStage = api(
  { method: "POST", path: "/commercial/leads/:id/stage", expose: true },
  async ({
    id,
    stage,
    authorization,
  }: {
    id: string;
    stage: string;
    authorization?: Header<"Authorization">;
  }): Promise<SalesLead> => {
    return updateLeadStageService(id, stage, authorization);
  }
);
