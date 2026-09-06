import { api, Header, Query } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getTaxObligationsService,
  syncComputedCorporateIncomeTaxService,
  upsertManualTaxObligationService,
  TaxObligationSummaryView,
  TaxObligationView,
  UpsertTaxObligationInput,
} from "../services/tax-obligation.service";

export interface GetTaxObligationsApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: Query<string>;
  periodId: Query<string>;
}

export const getTaxObligations = api(
  { method: "GET", path: "/finance/tax-obligations", expose: true },
  async (req: GetTaxObligationsApiRequest): Promise<TaxObligationSummaryView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return getTaxObligationsService(ctx, req.legalEntityId, req.periodId);
  }
);

export interface SyncTaxObligationApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: string;
  periodId: string;
}

export const postSyncTaxObligation = api(
  { method: "POST", path: "/finance/tax-obligations/sync", expose: true },
  async (req: SyncTaxObligationApiRequest): Promise<{ synced: TaxObligationView | null }> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    const synced = await syncComputedCorporateIncomeTaxService(ctx, req.legalEntityId, req.periodId);
    return { synced };
  }
);

export interface UpsertTaxObligationApiRequest extends UpsertTaxObligationInput {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const postTaxObligation = api(
  { method: "POST", path: "/finance/tax-obligations", expose: true },
  async (req: UpsertTaxObligationApiRequest): Promise<TaxObligationView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return upsertManualTaxObligationService(ctx, req);
  }
);
