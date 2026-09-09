import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { MvpSuccess, mvpItem } from "../../../shared/contracts/mvp-response";
import { FounderBriefView, getFounderBrief } from "../services/founder-brief.service";

export type { FounderBriefView };

export interface GetFounderBriefParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
}

// ── GET /operations/projects/:projectId/founder-brief ──
export const getFounderBriefEndpoint = api(
  { method: "GET", path: "/operations/projects/:projectId/founder-brief", expose: true },
  async (params: GetFounderBriefParams): Promise<MvpSuccess<FounderBriefView>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const brief = await getFounderBrief(ctx, params.projectId);
    return mvpItem(brief, [{ kind: "company_db", ref: "operations.founder_brief" }]);
  }
);
