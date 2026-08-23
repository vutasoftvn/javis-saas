import { api, Header } from "encore.dev/api";
import {
  LegalObligation,
  CreateObligationParams as BaseCreateObligationParams,
  createObligationService,
  getObligationService,
  fulfillObligationService,
} from "../services/legal-obligation.service";

export { LegalObligation };

export interface CreateObligationParams extends BaseCreateObligationParams {
  authorization?: Header<"Authorization">;
}

export interface ObligationByIdParams {
  id: number;
  authorization?: Header<"Authorization">;
}

export const createObligation = api(
  { method: "POST", path: "/finance-legal/obligations", expose: true },
  async (params: CreateObligationParams): Promise<LegalObligation> => {
    return createObligationService(params, params.authorization);
  }
);

export const getObligation = api(
  { method: "GET", path: "/finance-legal/obligations/:id", expose: true },
  async ({ id, authorization }: ObligationByIdParams): Promise<LegalObligation> => {
    return getObligationService(id, authorization);
  }
);

export const fulfillObligation = api(
  { method: "POST", path: "/finance-legal/obligations/:id/fulfill", expose: true },
  async ({ id, authorization }: ObligationByIdParams): Promise<LegalObligation> => {
    return fulfillObligationService(id, authorization);
  }
);
