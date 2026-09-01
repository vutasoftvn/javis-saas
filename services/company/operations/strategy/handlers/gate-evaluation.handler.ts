import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  GateEvaluation,
  BlockingRiskItem,
  RunGateEvaluationInput,
  ListGateEvaluationsInput,
  runGateEvaluationInWorkspace,
  getGateEvaluationInWorkspace,
  listGateEvaluationsInWorkspace,
  updateGateEvaluationInWorkspace,
  deleteGateEvaluationInWorkspace,
} from "../services/gate-evaluation.service";

export type { GateEvaluation, BlockingRiskItem };

export interface RunGateEvaluationParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string | number;
  stagePolicyId: string | number;
  blockingRisks?: BlockingRiskItem[];
}

export interface ListGateEvaluationsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
}

export const runGateEvaluation = api(
  { method: "POST", path: "/operations/strategy/gate-evaluations", expose: true },
  async (params: RunGateEvaluationParams): Promise<GateEvaluation> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return runGateEvaluationInWorkspace(ctx, params);
  }
);

export const getGateEvaluation = api(
  { method: "GET", path: "/operations/strategy/gate-evaluations/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<GateEvaluation> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getGateEvaluationInWorkspace(ctx, id);
  }
);

export const listGateEvaluations = api(
  { method: "GET", path: "/operations/strategy/gate-evaluations", expose: true },
  async (params: ListGateEvaluationsParams): Promise<{ items: GateEvaluation[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listGateEvaluationsInWorkspace(ctx, params);
  }
);

export const updateGateEvaluation = api(
  { method: "PATCH", path: "/operations/strategy/gate-evaluations/:id", expose: true },
  async ({ authorization, workspaceId, id, humanOverride, rationale }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string; humanOverride?: boolean; rationale?: string }): Promise<GateEvaluation> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return updateGateEvaluationInWorkspace(ctx, id, { humanOverride, rationale });
  }
);

export const deleteGateEvaluation = api(
  { method: "DELETE", path: "/operations/strategy/gate-evaluations/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return deleteGateEvaluationInWorkspace(ctx, id);
  }
);
