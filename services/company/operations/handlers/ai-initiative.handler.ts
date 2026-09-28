import { api, APIError, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  AiInitiative,
  createAiInitiativeInWorkspace,
  getAiInitiativeInWorkspace,
  InitiativeLifecycleState,
  InitiativeRiskTier,
  InitiativeAutonomyTier,
  InitiativeKind,
  InitiativeMilestone,
} from "../services/initiative.service";
import {
  transitionAiInitiative as transitionAiInitiativeService,
  AiInitiativeTransitionResult,
} from "../services/ai-initiative-transition.service";

export interface CreateAiInitiativeParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  title: string;
  description?: string;
  intendedOutcome?: string;
  businessProblem?: string;
  startDate?: string;
  targetDate?: string;
  milestones?: InitiativeMilestone[];
  businessOwnerMemberId: string;
  technicalOwnerMemberId?: string;
  riskOwnerMemberId?: string;
  keyResultIds: string[];
  riskTier?: InitiativeRiskTier;
  autonomyTier?: InitiativeAutonomyTier;
  initiativeKind?: InitiativeKind;
}

export interface GetAiInitiativeParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  initiativeId: string;
}

export interface TransitionAiInitiativeParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  initiativeId: string;
  targetState: InitiativeLifecycleState;
  expectedRevision: number;
  reasonCode: string;
  reason?: string;
  idempotencyKey?: string;
  humanEscalationRoute?: string;
  rollbackPauseProcedure?: string;
}

export const createAiInitiative = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/ai-initiatives",
  },
  async (params: CreateAiInitiativeParams): Promise<AiInitiative> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createAiInitiativeInWorkspace(ctx, params);
  }
);

export const getAiInitiative = api(
  {
    expose: true,
    method: "GET",
    path: "/operations/projects/:projectId/ai-initiatives/:initiativeId",
  },
  async (params: GetAiInitiativeParams): Promise<AiInitiative> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return getAiInitiativeInWorkspace(ctx, params);
  }
);

export const transitionAiInitiative = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/ai-initiatives/:initiativeId/transition",
  },
  async (
    params: TransitionAiInitiativeParams
  ): Promise<AiInitiativeTransitionResult> => {
    if (params.expectedRevision === undefined || params.expectedRevision === null) {
      throw APIError.invalidArgument("expectedRevision is required");
    }
    if (!params.reasonCode || params.reasonCode.trim().length === 0) {
      throw APIError.invalidArgument("reasonCode is required");
    }
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return transitionAiInitiativeService(
      {
        workspaceId: params.workspaceId,
        projectId: params.projectId,
        initiativeId: params.initiativeId,
        targetState: params.targetState,
        expectedRevision: params.expectedRevision,
        reasonCode: params.reasonCode,
        reason: params.reason,
        idempotencyKey: params.idempotencyKey,
        humanEscalationRoute: params.humanEscalationRoute,
        rollbackPauseProcedure: params.rollbackPauseProcedure,
      },
      ctx
    );
  }
);
