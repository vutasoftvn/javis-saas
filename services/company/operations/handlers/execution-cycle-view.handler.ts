import { api, Header, Query } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getExecutionCycleView,
  ExecutionCycleViewResponse,
} from "../services/execution-cycle-view.service";

export { ExecutionCycleViewResponse };

export interface GetExecutionCycleViewParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: Query<string>;
  cycleId?: Query<string>;
}

export const getExecutionCycleViewEndpoint = api(
  { method: "GET", path: "/operations/execution-cycle-view", expose: true },
  async (params: GetExecutionCycleViewParams): Promise<ExecutionCycleViewResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getExecutionCycleView(ctx, {
      projectId: params.projectId,
      cycleId: params.cycleId,
    });
  }
);
