import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  transitionProjectLifecycle,
  listProjectLifecycleEvents,
  ProjectLifecycleState,
  ProjectLifecycleEvent,
} from "../services/project-lifecycle.service";

export { ProjectLifecycleState, ProjectLifecycleEvent };

interface TransitionProjectLifecycleParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  toStage: string;
  expectedStageVersion: number;
  rationale?: string;
}

interface ListProjectLifecycleEventsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
}

export const transitionProjectLifecycleApi = api(
  { expose: true, method: "PATCH", path: "/operations/projects/:projectId/lifecycle" },
  async (params: TransitionProjectLifecycleParams): Promise<ProjectLifecycleState> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return transitionProjectLifecycle(ctx, params.projectId, {
      toStage: params.toStage,
      expectedStageVersion: params.expectedStageVersion,
      rationale: params.rationale,
    });
  }
);

export const listProjectLifecycleEventsApi = api(
  { expose: true, method: "GET", path: "/operations/projects/:projectId/lifecycle/events" },
  async (params: ListProjectLifecycleEventsParams): Promise<{ items: ProjectLifecycleEvent[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listProjectLifecycleEvents(ctx, params.projectId);
  }
);
