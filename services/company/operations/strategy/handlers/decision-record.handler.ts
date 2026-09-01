import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  DecisionRecord,
  StrategyDecision,
  CreateDecisionRecordInput,
  ListDecisionRecordsInput,
  createDecisionRecordInWorkspace,
  getDecisionRecordInWorkspace,
  listDecisionRecordsInWorkspace,
  deleteDecisionRecordInWorkspace,
} from "../services/decision-recording.service";

export type { DecisionRecord };

export interface CreateDecisionRecordParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
  gateEvaluationId?: string | number;
  decision: StrategyDecision;
  actorMemberId?: string | number;
  notes?: string;
}

export interface ListDecisionRecordsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
}

export const createDecisionRecord = api(
  { method: "POST", path: "/operations/strategy/decision-records", expose: true },
  async (params: CreateDecisionRecordParams): Promise<DecisionRecord> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createDecisionRecordInWorkspace(ctx, params);
  }
);

export const getDecisionRecord = api(
  { method: "GET", path: "/operations/strategy/decision-records/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<DecisionRecord> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getDecisionRecordInWorkspace(ctx, id);
  }
);

export const listDecisionRecords = api(
  { method: "GET", path: "/operations/strategy/decision-records", expose: true },
  async (params: ListDecisionRecordsParams): Promise<{ items: DecisionRecord[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return listDecisionRecordsInWorkspace(ctx, params);
  }
);

export const deleteDecisionRecord = api(
  { method: "DELETE", path: "/operations/strategy/decision-records/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return deleteDecisionRecordInWorkspace(ctx, id);
  }
);
