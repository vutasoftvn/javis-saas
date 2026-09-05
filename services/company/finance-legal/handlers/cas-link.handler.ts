import { api, Header } from "encore.dev/api";
import {
  createCasLinkSessionService,
  exchangeCasTokenService,
  revokeCasConnectionService,
  reauthorizeCasConnectionService,
  type CreateLinkSessionResult,
  type ExchangeTokenResult,
} from "../services/cas-link.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export interface CreateLinkSessionRequest {
  legalEntityId?: string;
  scopes: string[];
  returnPath?: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface ExchangeTokenRequest {
  sessionId: string;
  publicToken: string;
  stateHash: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface RevokeCasConnectionRequest {
  id: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface ReauthorizeCasConnectionRequest {
  id: string;
  newGrantId?: string;
  sameAccountVerified?: boolean;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export const createCasLinkSession = api(
  {
    method: "POST",
    path: "/finance/cas/link-sessions",
    expose: true,
  },
  async (params: CreateLinkSessionRequest): Promise<CreateLinkSessionResult> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createCasLinkSessionService({
      workspaceId: BigInt(ctx.workspaceId),
      legalEntityId: params.legalEntityId ? BigInt(params.legalEntityId) : undefined,
      createdBy: BigInt(ctx.userId),
      scopes: params.scopes,
      returnPath: params.returnPath,
    });
  }
);

export const exchangeCasLinkToken = api(
  {
    method: "POST",
    path: "/finance/cas/link-sessions/:sessionId/exchange",
    expose: true,
  },
  async (params: ExchangeTokenRequest): Promise<ExchangeTokenResult> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return exchangeCasTokenService({
      sessionId: params.sessionId,
      publicToken: params.publicToken,
      stateHash: params.stateHash,
      callerWorkspaceId: BigInt(ctx.workspaceId),
      callerUserId: BigInt(ctx.userId),
    });
  }
);

export const revokeCasConnection = api(
  {
    method: "POST",
    path: "/finance/bank-connections/:id/revoke",
    expose: true,
  },
  async (params: RevokeCasConnectionRequest): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return revokeCasConnectionService({
      connectionId: BigInt(params.id),
      workspaceId: BigInt(ctx.workspaceId),
    });
  }
);

export const reauthorizeCasConnection = api(
  {
    method: "POST",
    path: "/finance/bank-connections/:id/reauthorize",
    expose: true,
  },
  async (
    params: ReauthorizeCasConnectionRequest
  ): Promise<{ connectionId: string; consentState: string; needsReview: boolean }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return reauthorizeCasConnectionService({
      connectionId: BigInt(params.id),
      workspaceId: BigInt(ctx.workspaceId),
      newGrantId: params.newGrantId,
      sameAccountVerified: params.sameAccountVerified,
    });
  }
);
