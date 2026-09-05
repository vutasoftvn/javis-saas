import { api, Header } from "encore.dev/api";
import {
  LegalObligation,
  CreateObligationParams as BaseCreateObligationParams,
  createObligationService,
  getObligationService,
  fulfillObligationService,
} from "../services/legal-obligation.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export { LegalObligation };

export interface CreateObligationParams extends BaseCreateObligationParams {
  authorization?: Header<"Authorization">;
}

export interface ObligationByIdParams {
  id: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export const createObligation = api(
  { method: "POST", path: "/finance-legal/obligations", expose: true },
  async (params: CreateObligationParams): Promise<LegalObligation> => {
    return createObligationService(params, params.authorization);
  }
);

export const getObligation = api(
  { method: "GET", path: "/finance-legal/obligations/:id", expose: true },
  async ({ id, workspaceId, authorization }: ObligationByIdParams): Promise<LegalObligation> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getObligationService(id, ctx);
  }
);

export const fulfillObligation = api(
  { method: "POST", path: "/finance-legal/obligations/:id/fulfill", expose: true },
  async ({ id, workspaceId, authorization }: ObligationByIdParams): Promise<LegalObligation> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return fulfillObligationService(id, ctx);
  }
);

import { Query } from "encore.dev/api";
import {
  listObligationInstancesService,
  createObligationInstanceService,
  transitionObligationStatus,
  listObligationTransitions,
  LegalObligationInstanceView,
  ObligationTransitionView,
} from "../services/legal-obligation.service";

export interface ListObligationInstancesParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  status?: Query<string>;
}

export interface ListObligationInstancesResponse {
  instances: LegalObligationInstanceView[];
}

export interface CreateObligationInstanceParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  templateId?: string;
  regulationVersionId?: string;
  legalEntityProfileId?: string;
  source: "REGULATION_TEMPLATE" | "USER_CREATED" | "AI_PROPOSAL";
  title: string;
  dueDate?: string;
  periodKey?: string;
  evidenceRefs?: string[];
  evidenceArtifactId?: string;
  ownerMemberId?: string;
}

export interface TransitionObligationInstanceParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  expectedFromStatus?: string;
  toStatus: "OPEN" | "IN_PROGRESS" | "FULFILLED" | "EXEMPT" | "CANCELLED";
  evidenceArtifactId?: string;
  evidenceRefs?: string[];
  rationale?: string;
}

export interface ListObligationTransitionsParams {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const getObligationInstances = api(
  { method: "GET", path: "/legal/obligation-instances", expose: true },
  async (params: ListObligationInstancesParams): Promise<ListObligationInstancesResponse> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const instances = await listObligationInstancesService(
      BigInt(ctx.workspaceId),
      params.status
    );
    return { instances };
  }
);

export const postObligationInstance = api(
  { method: "POST", path: "/legal/obligation-instances", expose: true },
  async (params: CreateObligationInstanceParams): Promise<LegalObligationInstanceView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createObligationInstanceService({
      workspaceId: BigInt(ctx.workspaceId),
      templateId: params.templateId ? BigInt(params.templateId) : undefined,
      regulationVersionId: params.regulationVersionId
        ? BigInt(params.regulationVersionId)
        : undefined,
      legalEntityProfileId: params.legalEntityProfileId
        ? BigInt(params.legalEntityProfileId)
        : undefined,
      source: params.source,
      title: params.title,
      dueDate: params.dueDate,
      periodKey: params.periodKey,
      evidenceRefs: params.evidenceRefs,
      evidenceArtifactId: params.evidenceArtifactId
        ? BigInt(params.evidenceArtifactId)
        : undefined,
      ownerMemberId: params.ownerMemberId ? BigInt(params.ownerMemberId) : undefined,
    });
  }
);

export const transitionObligationInstanceApi = api(
  { method: "POST", path: "/legal/obligation-instances/:id/transition", expose: true },
  async (params: TransitionObligationInstanceParams): Promise<LegalObligationInstanceView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return transitionObligationStatus(
      {
        workspaceId: BigInt(ctx.workspaceId),
        instanceId: BigInt(params.id),
        expectedFromStatus: params.expectedFromStatus,
        toStatus: params.toStatus,
        evidenceArtifactId: params.evidenceArtifactId
          ? BigInt(params.evidenceArtifactId)
          : undefined,
        evidenceRefs: params.evidenceRefs,
        actorMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : undefined,
        rationale: params.rationale,
      },
      ctx
    );
  }
);

export const listObligationTransitionsApi = api(
  { method: "GET", path: "/legal/obligation-instances/:id/transitions", expose: true },
  async (params: ListObligationTransitionsParams): Promise<{ transitions: ObligationTransitionView[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const transitions = await listObligationTransitions(
      BigInt(ctx.workspaceId),
      BigInt(params.id)
    );
    return { transitions };
  }
);


