import { api, Header, Query } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  createBudgetEnvelopeService,
  getBudgetSummary,
  CreateBudgetEnvelopeInput,
  BudgetEnvelopeView,
  BudgetSummaryView,
} from "../services/budget-summary.service";

export interface CreateBudgetEnvelopeApiRequest extends CreateBudgetEnvelopeInput {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const postBudgetEnvelope = api(
  { method: "POST", path: "/finance/budget-envelopes", expose: true },
  async (req: CreateBudgetEnvelopeApiRequest): Promise<BudgetEnvelopeView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return createBudgetEnvelopeService(ctx, {
      projectId: req.projectId,
      legalEntityId: req.legalEntityId,
      currency: req.currency,
      periodStart: req.periodStart,
      periodEnd: req.periodEnd,
      limitMinor: req.limitMinor,
    });
  }
);

export interface GetBudgetSummaryApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: Query<string>;
  currency?: Query<string>;
}

export const getBudgetSummaryEndpoint = api(
  { method: "GET", path: "/finance/budget-summary", expose: true },
  async (req: GetBudgetSummaryApiRequest): Promise<BudgetSummaryView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return getBudgetSummary(ctx, req.projectId, req.currency ?? "VND");
  }
);
