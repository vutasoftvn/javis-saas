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
  // IA21: trước đây 3 field này không có trong request shape nên caller
  // KHÔNG thể chỉ định rõ cycle/tuần/version qua endpoint thật — luôn phải đi
  // qua đường tự suy luận (và khi suy luận thất bại, service từng âm thầm
  // mặc định tuần 1).
  cycleId?: string;
  weekNo?: number;
  expectedVersion?: number;
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
        cycleId: params.cycleId,
        weekNo: params.weekNo,
        expectedVersion: params.expectedVersion,
      },
      params.authorization
    );
  }
);
