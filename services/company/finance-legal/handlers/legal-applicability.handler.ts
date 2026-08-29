import { api, Header } from "encore.dev/api";
import {
  assessApplicableObligations,
  ApplicableObligationView,
} from "../services/legal-applicability.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export interface GetApplicableObligationsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export interface GetApplicableObligationsResponse {
  applicableObligations: ApplicableObligationView[];
}

export const getApplicableObligations = api(
  { method: "GET", path: "/legal/applicable-obligations", expose: true },
  async (params: GetApplicableObligationsParams): Promise<GetApplicableObligationsResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const obligations = await assessApplicableObligations(BigInt(ctx.workspaceId));
    return { applicableObligations: obligations };
  }
);
