import { api, Header, APIError } from "encore.dev/api";
import * as connectorSvc from "../services/workspace-connector.service";
import { requireWorkerServiceAuth } from "../services/token.service";
import { extractAuthContext } from "../middleware";

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
    const authCtx = extractAuthContext(params.authorization, params.workspaceId);

    // Verify caller is a member of the workspace
    await connectorSvc.verifyWorkspaceMembership(params.workspaceId, params.authorization);

    const res = await connectorSvc.installWorkspaceConnector({
      workspaceId: params.workspaceId,
      connectorKey: params.connectorKey,
      installedBy: authCtx.userID,
    });
    return res;
  }
);

export const registerAuthorizationEndpoint = api(
  { method: "POST", path: "/cosa/connectors/authorize", expose: true },
  async (params: AuthorizeConnectorParams): Promise<ConnectorAuthorizationResponse> => {
    const authCtx = extractAuthContext(params.authorization, params.workspaceId);

    // Verify caller is a member of the workspace
    await connectorSvc.verifyWorkspaceMembership(params.workspaceId, params.authorization);

    const res = await connectorSvc.registerConnectorAuthorization({
      installationId: params.installationId,
      workspaceId: params.workspaceId,
      principalId: authCtx.userID,
      secretRef: params.secretRef,
      grantedScopes: params.grantedScopes,
      expiresAt: new Date(params.expiresAt),
    });
    return res;
  }
);

// Các membershipRole được services/company xác nhận (không tự khai trong JWT của caller)
// coi là có quyền override quản lý connector authorization của principal khác.
// Khớp đúng với getRolePermissions() (services/company/identity/services/tenant-context.service.ts):
// chỉ "founder"/"co-founder" có toàn quyền ("*"); "admin" bị xếp chung với "member"/"user"
// (chỉ ["read","write"]) nên KHÔNG phải role đặc quyền — không tạo ngoại lệ riêng cho
// connector grant/revoke override (quyết định chính sách, review round 1/5, 2026-08-30).
const CONNECTOR_MANAGE_OTHERS_ROLES = new Set(["founder", "co-founder"]);

export const grantConnectorEndpoint = api(
  { method: "POST", path: "/cosa/connectors/grant", expose: true },
  async (params: GrantConnectorParams): Promise<SessionConnectorGrantResponse> => {
    const authCtx = extractAuthContext(params.authorization, params.workspaceId);

    // Verify caller is a member of the workspace, and lấy membershipRole đã được
    // services/company xác thực để xác định override founder/co-founder (không dùng role
    // tự khai trong JWT của caller).
    const membership = await connectorSvc.verifyWorkspaceMembership(params.workspaceId, params.authorization);
    const allowManageOthers = CONNECTOR_MANAGE_OTHERS_ROLES.has(membership.membershipRole);

    const res = await connectorSvc.grantConnectorToSession({
      workspaceId: params.workspaceId,
      conversationId: params.conversationId,
      authorizationId: params.authorizationId,
      grantedBy: authCtx.userID,
      allowedActions: params.allowedActions || [],
      expiresAt: params.expiresAt ? new Date(params.expiresAt) : null,
      callerPrincipalId: authCtx.userID,
      allowManageOthers,
    });
    return res;
  }
);

export const revokeGrantEndpoint = api(
  { method: "POST", path: "/cosa/connectors/revoke", expose: true },
  async (params: RevokeGrantParams) => {
    const authCtx = extractAuthContext(params.authorization, params.workspaceId);

    // Verify caller is a member of the workspace, và lấy membershipRole đã xác thực để
    // xác định override founder/co-founder.
    const membership = await connectorSvc.verifyWorkspaceMembership(params.workspaceId, params.authorization);
    const allowManageOthers = CONNECTOR_MANAGE_OTHERS_ROLES.has(membership.membershipRole);

    const res = await connectorSvc.revokeSessionGrant({
      workspaceId: params.workspaceId,
      conversationId: params.conversationId,
      grantId: params.grantId,
      callerPrincipalId: authCtx.userID,
      allowManageOthers,
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
