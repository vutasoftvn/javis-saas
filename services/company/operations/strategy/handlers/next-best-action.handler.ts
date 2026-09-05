import { api, Header, Query } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  assembleActionContextService,
  createActionProposalService,
  listActionProposalsService,
  ActionContext,
  NextBestActionView,
} from "../services/next-best-action.service";
import type {
  ProjectActionContext,
} from "../services/project-action-context.service";

export { NextBestActionView };

export interface AssembleContextParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const getActionContext = api(
  { method: "GET", path: "/operations/strategy/action-context", expose: true },
  async (params: AssembleContextParams): Promise<{ context: ActionContext }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const context = await assembleActionContextService(BigInt(ctx.workspaceId));
    return { context };
  }
);

export interface ListActionProposalsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  status?: Query<string>;
}

export const getActionProposals = api(
  { method: "GET", path: "/operations/strategy/action-proposals", expose: true },
  async (params: ListActionProposalsParams): Promise<{ proposals: NextBestActionView[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const proposals = await listActionProposalsService(BigInt(ctx.workspaceId), params.status);
    return { proposals };
  }
);

export interface GetNextBestActionsParams {
  id?: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: Query<string>;
}

export interface ProjectActionItemView {
  id: string;
  projectId: string;
  source: string;
  recommendation: string;
  priority: number;
  dueBy: string | null;
  status: string;
  decisionReason: string;
}

export interface NextBestActionsResultView {
  projectId: string;
  items: ProjectActionItemView[];
  status?: string;
  reason?: string;
}

export const getNextBestActions = api(
  { method: "GET", path: "/operations/strategy/projects/:id/next-best-actions", expose: true },
  async (params: GetNextBestActionsParams): Promise<NextBestActionsResultView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const pId = params.id || params.projectId || "0";
    const { proposeNextActions } = await import("../services/project-action-context.service");
    const result = await proposeNextActions(ctx, pId);
    return { projectId: pId, items: result.items, status: result.status, reason: result.reason };
  }
);

export interface GetProjectActionContextParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export interface GetProjectActionContextResponse {
  context: ProjectActionContext;
}

export const getProjectActionContextEndpoint = api(
  { method: "GET", path: "/operations/strategy/projects/:id/action-context", expose: true },
  async (params: GetProjectActionContextParams): Promise<GetProjectActionContextResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const { getProjectActionContext } = await import("../services/project-action-context.service");
    const context = await getProjectActionContext(ctx, params.id);
    return { context };
  }
);

export interface CreateActionProposalParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  source: "evidence" | "finance" | "legal" | "stage";
  recommendation: string;
  priority?: number;
  dueBy?: string;
  capabilityRequired?: string;
  decisionReason: string;
  contextSnapshot?: Record<string, unknown>;
  evidenceRefs?: unknown[];
  regulationRefs?: unknown[];
}

export const postActionProposal = api(
  { method: "POST", path: "/operations/strategy/action-proposals", expose: true },
  async (params: CreateActionProposalParams): Promise<NextBestActionView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const { toJsonObject, toJsonArray } = await import("../services/strategy-json");
    return createActionProposalService({
      workspaceId: BigInt(ctx.workspaceId),
      source: params.source,
      recommendation: params.recommendation,
      priority: params.priority,
      dueBy: params.dueBy,
      capabilityRequired: params.capabilityRequired,
      decisionReason: params.decisionReason,
      contextSnapshot: params.contextSnapshot ? toJsonObject(params.contextSnapshot) : undefined,
      evidenceRefs: params.evidenceRefs ? toJsonArray(params.evidenceRefs) : undefined,
      regulationRefs: params.regulationRefs ? toJsonArray(params.regulationRefs) : undefined,
    });
  }
);

export interface AcceptActionProposalParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  expectedVersion?: number;
  cycleId?: string;
  weekNo?: number;
}

export interface AcceptActionProposalResponse {
  proposalId: string;
  status: string;
  decisionId: string;
  commitmentId: string | null;
  revision: number;
}

export const postAcceptActionProposal = api(
  { method: "POST", path: "/operations/strategy/action-proposals/:id/accept", expose: true },
  async (params: AcceptActionProposalParams): Promise<AcceptActionProposalResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const { acceptActionProposal } = await import("../services/project-action-context.service");
    return acceptActionProposal(ctx, {
      proposalId: params.id,
      expectedVersion: params.expectedVersion,
      cycleId: params.cycleId,
      weekNo: params.weekNo,
    });
  }
);
