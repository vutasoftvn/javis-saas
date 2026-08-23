import { api, Header } from "encore.dev/api";
import { Initiative, CreateInitiativeParams as BaseCreateInitiativeParams, createInitiativeService, getInitiativeService } from "../services/initiative.service";

export { Initiative };

export interface CreateInitiativeParams extends BaseCreateInitiativeParams {
  authorization?: Header<"Authorization">;
}

export const createInitiative = api(
  { method: "POST", path: "/operations/initiatives", expose: true },
  async (params: CreateInitiativeParams): Promise<Initiative> => {
    return createInitiativeService(params, params.authorization);
  }
);

export const getInitiative = api(
  { method: "GET", path: "/operations/initiatives/:id", expose: true },
  async ({ id, authorization }: { id: number; authorization?: Header<"Authorization"> }): Promise<Initiative> => {
    return getInitiativeService(id, authorization);
  }
);
