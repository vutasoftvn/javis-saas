import { api, Header } from "encore.dev/api";
import * as connectorSvc from "../services/workspace-connector.service";
import { verifyPlatformToken, requireWorkerServiceAuth } from "../services/token.service";

export interface InstallConnectorParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  connectorKey: string;
}

export interface AuthorizeConnectorParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  installationId: string;
  secretRef: string;
  grantedScopes: string[];
  expiresAt: string; // ISO date string
}

export interface GrantConnectorParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  conversationId: string;
  authorizationId: string;
  allowedActions?: string[];
  expiresAt?: string;
}

export interface RevokeGrantParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  conversationId: string;
  grantId: string;
}

export interface AssertConnectorParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  conversationId: string;
  connectorKey: string;
  action?: string;
  requiredScope?: string;
}

export interface ConnectorInstallationResponse {
  id: string;
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
  grantedScopes: string[];
  state: string;
  expiresAt: Date;
  hasSecret: boolean;
}

export interface SessionConnectorGrantResponse {
  id: string;
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
  // secretRef is a vault reference (not a raw secret), returned only to the worker-only /cosa/connectors/assert endpoint (gated by requireWorkerServiceAuth)
  secretRef?: string;
  error?: string;
}

export const installConnectorEndpoint = api(
  { method: "POST", path: "/cosa/connectors/install", expose: true },
  async (params: InstallConnectorParams): Promise<ConnectorInstallationResponse> => {
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);

    // Verify caller is a member of the workspace by checking with services/company
    const companyUrl = process.env.COMPANY_SERVICE_URL || "http://localhost:4002";
    try {
      const response = await fetch(`${companyUrl}/identity/workspaces/${params.workspaceId}/platform-company`, {
        method: "GET",
        headers: {
          "Authorization": params.authorization,
          "Content-Type": "application/json",
        },
      });

      if (response.status === 403 || response.status === 401) {
        throw new Error("not a member of this workspace");
      }
      if (!response.ok) {
        throw new Error(`workspace verification failed: ${response.status}`);
      }
    } catch (err) {
      throw new Error(`failed to verify workspace membership: ${err instanceof Error ? err.message : String(err)}`);
    }

    const res = await connectorSvc.installWorkspaceConnector({
      workspaceId: params.workspaceId,
      connectorKey: params.connectorKey,
      installedBy: claims.sub,
    });
    return res;
  }
);

export const registerAuthorizationEndpoint = api(
  { method: "POST", path: "/cosa/connectors/authorize", expose: true },
  async (params: AuthorizeConnectorParams): Promise<ConnectorAuthorizationResponse> => {
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);

    const res = await connectorSvc.registerConnectorAuthorization({
      installationId: params.installationId,
      workspaceId: params.workspaceId,
      principalId: claims.sub,
      secretRef: params.secretRef,
      grantedScopes: params.grantedScopes,
      expiresAt: new Date(params.expiresAt),
    });
    return res;
  }
);

export const grantConnectorEndpoint = api(
  { method: "POST", path: "/cosa/connectors/grant", expose: true },
  async (params: GrantConnectorParams): Promise<SessionConnectorGrantResponse> => {
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);

    const res = await connectorSvc.grantConnectorToSession({
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
    verifyPlatformToken(token);

    const res = await connectorSvc.revokeSessionGrant({
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
      workspaceId: params.workspaceId,
      conversationId: params.conversationId,
      connectorKey: params.connectorKey,
      action: params.action,
      requiredScope: params.requiredScope,
    });
    return res;
  }
);
