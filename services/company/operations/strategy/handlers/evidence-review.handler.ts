import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { Evidence } from "../services/evidence-lifecycle.service";
import { reviewEvidenceInWorkspace } from "../services/evidence-review.service";

export interface ReviewEvidenceParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  action: "approve" | "reject";
  comment?: string;
}

export const reviewEvidence = api(
  { method: "POST", path: "/operations/strategy/evidence/:id/review", expose: true },
  async (params: ReviewEvidenceParams): Promise<Evidence> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return reviewEvidenceInWorkspace(ctx, params);
  }
);
