import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  transitionWorkspaceLifecycle,
  listWorkspaceLifecycleEvents,
  WorkspaceLifecycleState,
  WorkspaceLifecycleEvent,
} from "../services/workspace-lifecycle.service";

export { WorkspaceLifecycleState, WorkspaceLifecycleEvent };

interface TransitionWorkspaceLifecycleParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  toStage: string;
  expectedStageVersion: number;
  rationale?: string;
}

interface ListWorkspaceLifecycleEventsParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
}

export const transitionWorkspaceLifecycleApi = api(
  { expose: true, method: "PATCH", path: "/identity/workspaces/:workspaceId/lifecycle" },
  async (params: TransitionWorkspaceLifecycleParams): Promise<WorkspaceLifecycleState> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return transitionWorkspaceLifecycle(ctx, params.workspaceId, {
      toStage: params.toStage,
      expectedStageVersion: params.expectedStageVersion,
      rationale: params.rationale,
    });
  }
);

export const listWorkspaceLifecycleEventsApi = api(
  { expose: true, method: "GET", path: "/identity/workspaces/:workspaceId/lifecycle/events" },
  async (params: ListWorkspaceLifecycleEventsParams): Promise<{ items: WorkspaceLifecycleEvent[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listWorkspaceLifecycleEvents(ctx, params.workspaceId);
  }
);
