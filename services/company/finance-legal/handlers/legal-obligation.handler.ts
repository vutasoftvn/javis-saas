import { api, Header } from "encore.dev/api";
import {
  LegalObligation,
  CreateObligationParams as BaseCreateObligationParams,
  createObligationService,
  getObligationService,
  fulfillObligationService,
} from "../services/legal-obligation.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export { LegalObligation };

export interface CreateObligationParams extends BaseCreateObligationParams {
  authorization?: Header<"Authorization">;
}

export interface ObligationByIdParams {
  id: string;
  workspaceId: Header<"X-Workspace-Id">;
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
  async ({ id, workspaceId, authorization }: ObligationByIdParams): Promise<LegalObligation> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getObligationService(id, ctx);
  }
);

export const fulfillObligation = api(
  { method: "POST", path: "/finance-legal/obligations/:id/fulfill", expose: true },
  async ({ id, workspaceId, authorization }: ObligationByIdParams): Promise<LegalObligation> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return fulfillObligationService(id, ctx);
  }
);

