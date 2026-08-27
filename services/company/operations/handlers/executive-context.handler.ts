import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { getExecutiveContextService, ExecutiveContextSnapshot } from "../services/executive-context.service";

/**
 * GET /operations/executive-context
 *
 * Trả về workspace-scoped Executive Context Snapshot — aggregate của tasks, objectives, projects
 * với evidence refs stable và workspace isolation.
 *
 * Query parameters:
 * - focus: "delivery_risk" | "objectives" | "general" (optional)
 * - limit: số lượng evidence items (server clamp 1..50)
 *
 * NOT accepting workspaceId từ request — derive từ TenantContext/Authorization + X-Workspace-Id
 */
export const getExecutiveContext = api(
  { method: "GET", path: "/operations/executive-context", expose: true },
  async ({
    workspaceId,
    authorization,
    focus,
    limit,
  }: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    focus?: "delivery_risk" | "objectives" | "general";
    limit?: number;
  }): Promise<ExecutiveContextSnapshot> => {
    // Resolve TenantContext từ Authorization + X-Workspace-Id
    // Throw nếu caller không member của workspace này
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);

    // Query snapshot từ workspace của caller
    return getExecutiveContextService(ctx, {
      workspaceId: ctx.workspaceId,
      focus,
      limit,
    });
  }
);
