import { api, APIError, Header } from "encore.dev/api";
import {
  setWeeklyGoalService,
  SetWeeklyGoalResult,
} from "../services/weekly-goal.service";

export interface SetWeeklyGoalParams {
  id: string; // projectId (path)
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  focus: string;
  mission?: string;
  triggerDecomposition?: boolean;
  origin?: "command_center" | "chat";
  originRef?: string;
}

export const setWeeklyGoal = api(
  { method: "POST", path: "/operations/strategy/projects/:id/weekly-goal", expose: true },
  async (params: SetWeeklyGoalParams): Promise<SetWeeklyGoalResult> => {
    if (!params.workspaceId) throw APIError.invalidArgument("X-Workspace-Id header required");
    if (!params.focus || !params.focus.trim()) {
      throw APIError.invalidArgument("focus required");
    }
    return setWeeklyGoalService(
      {
        projectId: params.id,
        workspaceId: params.workspaceId,
        focus: params.focus,
        mission: params.mission ?? null,
        triggerDecomposition: params.triggerDecomposition ?? false,
        origin: params.origin ?? "command_center",
        originRef: params.originRef ?? null,
      },
      params.authorization
    );
  }
);
