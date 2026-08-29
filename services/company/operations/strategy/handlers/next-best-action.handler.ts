import { api, Header, Query } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  assembleActionContextService,
  createActionProposalService,
  listActionProposalsService,
  acceptActionProposalService,
  generateAndRankNextActions,
  NextBestActionView,
} from "../services/next-best-action.service";


export interface AssembleContextParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const getActionContext = api(
  { method: "GET", path: "/operations/strategy/action-context", expose: true },
  async (params: AssembleContextParams): Promise<{ context: any }> => {
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

export const getNextBestActions = api(
  { method: "GET", path: "/operations/strategy/projects/:id/next-best-actions", expose: true },
  async (params: GetNextBestActionsParams): Promise<{ projectId: string; items: any[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const pId = params.id || params.projectId || "0";
    const items = generateAndRankNextActions({
      projectId: Number(pId),
      untestedAssumptions: [{ id: 1, statement: "Customer problem validation", importance: 8, uncertainty: 8 }],
    });
    return { projectId: pId, items };
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
  contextSnapshot?: any;
  evidenceRefs?: any[];
  regulationRefs?: any[];
}

export const postActionProposal = api(
  { method: "POST", path: "/operations/strategy/action-proposals", expose: true },
  async (params: CreateActionProposalParams): Promise<NextBestActionView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createActionProposalService({
      workspaceId: BigInt(ctx.workspaceId),
      source: params.source,
      recommendation: params.recommendation,
      priority: params.priority,
      dueBy: params.dueBy,
      capabilityRequired: params.capabilityRequired,
      decisionReason: params.decisionReason,
      contextSnapshot: params.contextSnapshot,
      evidenceRefs: params.evidenceRefs,
      regulationRefs: params.regulationRefs,
    });
  }
);

export interface AcceptActionProposalParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const postAcceptActionProposal = api(
  { method: "POST", path: "/operations/strategy/action-proposals/:id/accept", expose: true },
  async (params: AcceptActionProposalParams): Promise<NextBestActionView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return acceptActionProposalService({
      proposalId: BigInt(params.id),
      acceptedBy: BigInt(ctx.userId || "1"),
    });
  }
);
