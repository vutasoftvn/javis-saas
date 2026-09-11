import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  createDraftDeliberation,
  frameDeliberation,
  cancelDeliberation,
  appendFounderDecision,
  getDeliberation,
  DeliberationDetails,
  DeliberationState,
  ExecutiveDecisionType,
  EvidenceSourceInput,
} from "../services/executive-deliberation.service";

interface CreateDraftDeliberationParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  title: string;
}

export const createDraftDeliberationApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/deliberations/draft",
  },
  async (
    params: CreateDraftDeliberationParams
  ): Promise<{ id: string; title: string; state: DeliberationState; version: number }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await createDraftDeliberation(ctx, params.projectId, {
      title: params.title,
    });
  }
);

interface FrameDeliberationParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  deliberationId: string;
  question: string;
  roleKeys: string[];
  expectedVersion?: number;
  deliberationType?: string;
  deadline?: string;
  evidenceSources?: EvidenceSourceInput[];
  criticRequired?: boolean;
  redactedContextRef?: string;
  idempotencyKey?: string;
}

export const frameDeliberationApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/deliberations/:deliberationId/frame",
  },
  async (
    params: FrameDeliberationParams
  ): Promise<{ id: string; state: DeliberationState; activeFrameVersion: number; version: number }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await frameDeliberation(ctx, params.projectId, params.deliberationId, {
      expectedVersion: params.expectedVersion,
      question: params.question,
      roleKeys: params.roleKeys,
      deliberationType: params.deliberationType,
      deadline: params.deadline,
      evidenceSources: params.evidenceSources,
      criticRequired: params.criticRequired,
      redactedContextRef: params.redactedContextRef,
      idempotencyKey: params.idempotencyKey,
    });
  }
);

interface CancelDeliberationParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  deliberationId: string;
  expectedVersion?: number;
  reason?: string;
}

export const cancelDeliberationApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/deliberations/:deliberationId/cancel",
  },
  async (
    params: CancelDeliberationParams
  ): Promise<{ id: string; state: DeliberationState; version: number }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await cancelDeliberation(ctx, params.projectId, params.deliberationId, {
      expectedVersion: params.expectedVersion,
      reason: params.reason,
    });
  }
);

interface AppendFounderDecisionParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  deliberationId: string;
  decisionType: ExecutiveDecisionType;
  expectedVersion?: number;
  notes?: string;
  modifications?: Record<string, any>;
}

export const appendFounderDecisionApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/deliberations/:deliberationId/decision",
  },
  async (
    params: AppendFounderDecisionParams
  ): Promise<{ id: string; deliberationId: string; decisionType: ExecutiveDecisionType; version: number }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await appendFounderDecision(ctx, params.projectId, params.deliberationId, {
      decisionType: params.decisionType,
      expectedVersion: params.expectedVersion,
      notes: params.notes,
      modifications: params.modifications,
    });
  }
);

interface GetDeliberationParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  deliberationId: string;
}

export const getDeliberationApi = api(
  {
    expose: true,
    method: "GET",
    path: "/operations/projects/:projectId/deliberations/:deliberationId",
  },
  async (
    params: GetDeliberationParams
  ): Promise<DeliberationDetails> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await getDeliberation(ctx, params.projectId, params.deliberationId);
  }
);
