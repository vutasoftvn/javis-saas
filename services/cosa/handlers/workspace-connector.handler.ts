import { api, Header } from "encore.dev/api";
import * as connectorSvc from "../services/workspace-connector.service";
import { validateUserMembership } from "../services/company.service";
import { verifyPlatformToken, requireWorkerServiceAuth } from "../services/token.service";

export interface InstallConnectorParams {
  authorization?: Header<"Authorization">;
  companyId: string;
  workspaceId: string;
  connectorKey: string;
}

export interface AuthorizeConnectorParams {
  authorization?: Header<"Authorization">;
  companyId: string;
  workspaceId: string;
  installationId: string;
  secretRef: string;
  grantedScopes: string[];
  expiresAt: string; // ISO date string
}

export interface GrantConnectorParams {
  authorization?: Header<"Authorization">;
  companyId: string;
  workspaceId: string;
  conversationId: string;
  authorizationId: string;
  allowedActions?: string[];
  expiresAt?: string;
}

export interface RevokeGrantParams {
  authorization?: Header<"Authorization">;
  companyId: string;
  workspaceId: string;
  conversationId: string;
  grantId: string;
}

export interface AssertConnectorParams {
  authorization?: Header<"Authorization">;
  companyId: string;
  workspaceId: string;
  conversationId: string;
  connectorKey: string;
  action?: string;
  requiredScope?: string;
}

export interface ConnectorInstallationResponse {
  id: string;
  companyId: string;
  workspaceId: string;
  connectorKey: string;
  installedBy: string;
  status: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface ConnectorAuthorizationResponse {
  id: string;
  installationId: string;
  principalId: string;
  secretRef?: string; // Excluded from response (never sent)
  grantedScopes: string[];
  state: string;
  expiresAt: Date;
  revokedAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface SessionConnectorGrantResponse {
  id: string;
  companyId: string;
  workspaceId: string;
  conversationId: string;
  authorizationId: string;
  grantedBy: string;
  allowedActions: string[];
  state: string;
  expiresAt: Date | null;
  revokedAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface ConnectorAssertResponse {
  ok: boolean;
  reason?: string;
}

export const installConnectorEndpoint = api(
  { method: "POST", path: "/cosa/connectors/install", expose: true },
  async (params: InstallConnectorParams): Promise<ConnectorInstallationResponse> => {
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);
    await validateUserMembership({ platformToken: token, companyId: params.companyId });

    const res = await connectorSvc.installWorkspaceConnector({
      companyId: params.companyId,
      workspaceId: params.workspaceId,
      connectorKey: params.connectorKey,
      installedBy: claims.sub,
    });
    return res;
  }
);

export const registerAuthorizationEndpoint = api(
  { method: "POST", path: "/cosa/connectors/authorize", expose: true },
  async (params: AuthorizeConnectorParams): Promise<Omit<ConnectorAuthorizationResponse, 'secretRef'>> => {
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);
    await validateUserMembership({ platformToken: token, companyId: params.companyId });

    const res = await connectorSvc.registerConnectorAuthorization({
      installationId: params.installationId,
      companyId: params.companyId,
      workspaceId: params.workspaceId,
      principalId: claims.sub,
      secretRef: params.secretRef,
      grantedScopes: params.grantedScopes,
      expiresAt: new Date(params.expiresAt),
    });
    // Exclude secretRef from response
    const { secretRef, ...response } = res;
    return response as Omit<ConnectorAuthorizationResponse, 'secretRef'>;
  }
);

export const grantConnectorEndpoint = api(
  { method: "POST", path: "/cosa/connectors/grant", expose: true },
  async (params: GrantConnectorParams): Promise<SessionConnectorGrantResponse> => {
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);
    await validateUserMembership({ platformToken: token, companyId: params.companyId });

    const res = await connectorSvc.grantConnectorToSession({
      companyId: params.companyId,
      workspaceId: params.workspaceId,
      conversationId: params.conversationId,
      authorizationId: params.authorizationId,
      grantedBy: claims.sub,
      allowedActions: params.allowedActions || [],
      expiresAt: params.expiresAt ? new Date(params.expiresAt) : null,
    });
    return res;
  }
);

export const revokeGrantEndpoint = api(
  { method: "POST", path: "/cosa/connectors/revoke", expose: true },
  async (params: RevokeGrantParams) => {
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    await validateUserMembership({ platformToken: token, companyId: params.companyId });

    const res = await connectorSvc.revokeSessionGrant({
      companyId: params.companyId,
      workspaceId: params.workspaceId,
      conversationId: params.conversationId,
      grantId: params.grantId,
    });
    return { ok: !!res };
  }
);

export const assertConnectorEndpoint = api(
  { method: "POST", path: "/cosa/connectors/assert", expose: true },
  async (params: AssertConnectorParams): Promise<ConnectorAssertResponse> => {
    // Worker authentication guard
    requireWorkerServiceAuth(params.authorization);

    const res = await connectorSvc.assertConnectorInvocation({
      companyId: params.companyId,
      workspaceId: params.workspaceId,
      conversationId: params.conversationId,
      connectorKey: params.connectorKey,
      action: params.action,
      requiredScope: params.requiredScope,
    });
    return res;
  }
);
