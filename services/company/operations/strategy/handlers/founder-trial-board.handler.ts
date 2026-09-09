import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { MvpSuccess, mvpItem } from "../../../shared/contracts/mvp-response";
import {
  FounderTrialBoardView,
  getFounderTrialBoard,
} from "../services/founder-trial-board.service";

export type { FounderTrialBoardView };

export interface GetFounderTrialBoardParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
}

// ── GET /operations/projects/:projectId/founder-trial-board ──
export const getFounderTrialBoardEndpoint = api(
  { method: "GET", path: "/operations/projects/:projectId/founder-trial-board", expose: true },
  async (params: GetFounderTrialBoardParams): Promise<MvpSuccess<FounderTrialBoardView>> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const board = await getFounderTrialBoard(ctx, params.projectId);
    return mvpItem(board, [{ kind: "company_db", ref: "operations.founder_trial_board" }]);
  }
);
