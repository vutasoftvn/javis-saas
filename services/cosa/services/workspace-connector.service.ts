import { APIError } from "encore.dev/api";
import { eq, and, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { isStagingOrProd } from "../shared/env";
import { verifyControlDelegationToken } from "./token.service";
import { authorizeAndProjectCoreAccess, looksLikeJwt } from "./core-access.service";

const DEV_COMPANY_SERVICE_URL = "http://localhost:4002";

function resolveCompanyServiceUrl(): string {
  const url = process.env.COMPANY_SERVICE_URL;
  if (isStagingOrProd()) {
    if (!url || url === DEV_COMPANY_SERVICE_URL) {
      throw new Error("COMPANY_SERVICE_URL must be explicitly set in staging/production, cannot use default URL");
    }
  }
  return url || DEV_COMPANY_SERVICE_URL;
}

const {
  workspaceConnectorInstallations,
  connectorAuthorizations,
  sessionConnectorGrants,
} = schema;

export type ConnectorAuthorizationState = "active" | "expired" | "revoked";
export type SessionConnectorGrantState = "enabled" | "revoked" | "expired";

export const CONNECTOR_SCOPE_ALLOWLIST: Record<string, string[]> = {
  "sandbox-read": ["read", "read:data", "metadata"],
  "cas": ["balance:read", "transactions:read"],
};


export function getAllowedConnectorKeys(): string[] {
  const envVal = process.env.COSA_CONNECTOR_ALLOWED_KEYS || "sandbox-read";
  return envVal.split(",").map((s) => s.trim()).filter(Boolean);
}

export function assertConnectorKeyAllowed(key: string): void {
  const allowed = getAllowedConnectorKeys();
  if (!allowed.includes(key)) {
    throw APIError.invalidArgument(`connector_key '${key}' is not allowed in current test capability set`);
  }
}

export function validateConnectorScopes(connectorKey: string, scopes: string[]): void {
  const allowlist = CONNECTOR_SCOPE_ALLOWLIST[connectorKey];
  if (!allowlist) {
    throw APIError.invalidArgument(`Unknown connector key '${connectorKey}'`);
  }
  for (const s of scopes) {
    if (!allowlist.includes(s)) {
      throw APIError.invalidArgument(
        `Scope '${s}' is not allowed for connector '${connectorKey}'. Only read-only scopes are permitted.`
      );
    }
  }
}

export function validateSecretRef(secretRef: string): void {
  if (!secretRef || !secretRef.startsWith("secret://cosa-connectors/")) {
    throw APIError.invalidArgument("secret_ref must use the cosa-connectors vault namespace");
  }
}

export interface WorkspaceMembershipInfo {
  platformCompanyId: string | null;
  membershipRole: string;
}

/**
 * Verify that a user (identified by authorization header) is a member of the given workspace.
 * Called to services/company /identity/workspaces/:id/platform-company endpoint.
 *
 * Returns workspace membership info if successful. Throws APIError on auth/permission failures.
 * - 401/403 from services/company → APIError.permissionDenied (not a workspace member)
 * - Network error or non-2xx from services/company → APIError.unavailable
 */
export async function verifyWorkspaceMembership(
  organizationId: string,
  authorizationHeader: string | undefined
): Promise<WorkspaceMembershipInfo> {
  // Access token OIDC của core: core quyết định thành viên.
  const bearer = authorizationHeader?.replace(/^Bearer\s+/i, "");
  if (!bearer) {
    throw APIError.unauthenticated("invalid or expired access token");
  }
  // Control-plane delegation do apps/cosa ký (đã kiểm tra thành viên thật): tin claim, không hỏi lại core.
  if (looksLikeJwt(bearer)) {
    const delegation = verifyControlDelegationToken(bearer);
    if (delegation.organizationId !== organizationId) {
      throw APIError.permissionDenied("control-plane delegation token scoped cho workspace khác");
    }
    return { platformCompanyId: null, membershipRole: delegation.role };
  }
  const access = await authorizeAndProjectCoreAccess(bearer, organizationId, "cosa.workspace.read");
  return { platformCompanyId: null, membershipRole: access.cosaRole };
}

/**
 * Điểm vào DÙNG CHUNG cho mọi endpoint cần "caller đã chứng minh thuộc workspace này"
 * (agent-policy-snapshot, /cosa/schedules*). Ưu tiên control-plane delegation (apps/cosa tự mint sau khi
 * đã cross-check membership thật — xem apps/cosa/auth/jwt.py::mint_control_plane_delegation) — TIN claim
 * organizationId/sub trong đó. Nếu không phải delegation hợp lệ thì là access token OIDC của core: core quyết
 * định thành viên (introspect + `/me/organizations/:id/authorize`).
 */
export async function resolveCallerAuthorizedForWorkspace(
  authorizationHeader: string | undefined,
  organizationId: string
): Promise<{ sub: string }> {
  if (!authorizationHeader) {
    throw APIError.unauthenticated("missing authorization header");
  }
  const token = authorizationHeader.replace(/^Bearer\s+/i, "");

  try {
    const delegation = verifyControlDelegationToken(token);
    if (delegation.organizationId !== organizationId) {
      throw APIError.permissionDenied("control-plane delegation token scoped cho workspace khác");
    }
    return { sub: delegation.sub };
  } catch (err) {
    if (err instanceof APIError && err.code === "permission_denied") {
      throw err;
    }
    // Không phải delegation token hợp lệ -> access token OIDC của core.
  }

  if (looksLikeJwt(token)) {
    throw APIError.unauthenticated("invalid or expired access token");
  }
  const access = await authorizeAndProjectCoreAccess(token, organizationId, "cosa.workspace.read");
  return { sub: access.userId };
}

export async function installWorkspaceConnector(input: {
  organizationId: string;
  connectorKey: string;
  installedBy: string;
}) {
  assertConnectorKeyAllowed(input.connectorKey);

  const existing = await db
    .select()
    .from(workspaceConnectorInstallations)
    .where(
      and(
        eq(workspaceConnectorInstallations.organizationId, input.organizationId),
        eq(workspaceConnectorInstallations.connectorKey, input.connectorKey)
      )
    );

  if (existing.length > 0) {
    if (existing[0].status !== "enabled") {
      await db
        .update(workspaceConnectorInstallations)
        .set({ status: "enabled", updatedAt: new Date() })
        .where(eq(workspaceConnectorInstallations.id, existing[0].id));
      existing[0].status = "enabled";
    }
    return existing[0];
  }

  const id = `conn_inst_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  const [created] = await db
    .insert(workspaceConnectorInstallations)
    .values({
      id,
      organizationId: input.organizationId,
      connectorKey: input.connectorKey,
      installedBy: input.installedBy,
      status: "enabled",
    })
    .returning();

  return created;
}

export async function registerConnectorAuthorization(input: {
  installationId: string;
  organizationId: string;
  principalId: string;
  secretRef: string;
  grantedScopes: string[];
  expiresAt: Date;
}) {
  validateSecretRef(input.secretRef);

  const [installation] = await db
    .select()
    .from(workspaceConnectorInstallations)
    .where(
      and(
        eq(workspaceConnectorInstallations.id, input.installationId),
        eq(workspaceConnectorInstallations.organizationId, input.organizationId)
      )
    );

  if (!installation) throw APIError.notFound("connector installation not found");
  if (installation.status !== "enabled") {
    throw APIError.failedPrecondition("connector installation is disabled");
  }

  validateConnectorScopes(installation.connectorKey, input.grantedScopes);

  const id = `conn_auth_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  const [created] = await db
    .insert(connectorAuthorizations)
    .values({
      id,
      installationId: input.installationId,
      organizationId: input.organizationId,
      principalId: input.principalId,
      secretRef: input.secretRef,
      grantedScopes: input.grantedScopes,
      state: "active",
      expiresAt: input.expiresAt,
    })
    .returning();

  return {
    id: created.id,
    installationId: created.installationId,
    principalId: created.principalId,
    grantedScopes: created.grantedScopes,
    state: created.state as ConnectorAuthorizationState,
    expiresAt: created.expiresAt,
    hasSecret: true,
  };
}

export async function grantConnectorToSession(input: {
  organizationId: string;
  conversationId: string;
  authorizationId: string;
  grantedBy: string;
  allowedActions: string[];
  expiresAt?: Date | null;
  // Danh tính người gọi thực (đã xác thực) và cờ override đã được kiểm tra ở tầng
  // handler dựa trên membershipRole do services/company xác nhận — không tự suy diễn ở đây.
  callerPrincipalId: string;
  allowManageOthers: boolean;
}) {
  const [auth] = await db
    .select()
    .from(connectorAuthorizations)
    .innerJoin(
      workspaceConnectorInstallations,
      eq(connectorAuthorizations.installationId, workspaceConnectorInstallations.id)
    )
    .where(
      and(
        eq(connectorAuthorizations.id, input.authorizationId),
        eq(workspaceConnectorInstallations.organizationId, input.organizationId)
      )
    );

  if (!auth) {
    throw APIError.notFound("connector authorization not found");
  }

  const authRecord = auth.connector_authorizations;

  // Một member chỉ được thao tác trên connector authorization của chính mình, trừ khi
  // có override founder/co-founder đã qua kiểm tra (audited) từ tầng gọi.
  if (authRecord.principalId !== input.callerPrincipalId && !input.allowManageOthers) {
    throw APIError.permissionDenied(
      "connector authorization belongs to another principal (authorization owner mismatch)"
    );
  }

  if (authRecord.state !== "active" || authRecord.expiresAt < new Date()) {
    throw APIError.failedPrecondition("connector authorization requires reauthorization");
  }

  const existingGrant = await db
    .select()
    .from(sessionConnectorGrants)
    .where(
      and(
        eq(sessionConnectorGrants.conversationId, input.conversationId),
        eq(sessionConnectorGrants.authorizationId, input.authorizationId)
      )
    );

  if (existingGrant.length > 0) {
    const [updated] = await db
      .update(sessionConnectorGrants)
      .set({
        state: "enabled",
        allowedActions: input.allowedActions,
        expiresAt: input.expiresAt || null,
        revokedAt: null,
        updatedAt: new Date(),
      })
      .where(eq(sessionConnectorGrants.id, existingGrant[0].id))
      .returning();
    return updated;
  }

  const id = `sess_grant_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  const [created] = await db
    .insert(sessionConnectorGrants)
    .values({
      id,
      organizationId: input.organizationId,
      conversationId: input.conversationId,
      authorizationId: input.authorizationId,
      grantedBy: input.grantedBy,
      allowedActions: input.allowedActions,
      state: "enabled",
      expiresAt: input.expiresAt || null,
    })
    .returning();

  return created;
}

export async function revokeSessionGrant(input: {
  organizationId: string;
  conversationId: string;
  grantId: string;
  callerPrincipalId: string;
  allowManageOthers: boolean;
}) {
  // Load grant cùng authorization (cùng workspace + conversation) trước khi ghi, để biết
  // ai là chủ sở hữu authorization đứng sau session grant này.
  const [row] = await db
    .select({
      grant: sessionConnectorGrants,
      auth: connectorAuthorizations,
    })
    .from(sessionConnectorGrants)
    .innerJoin(connectorAuthorizations, eq(sessionConnectorGrants.authorizationId, connectorAuthorizations.id))
    .where(
      and(
        eq(sessionConnectorGrants.id, input.grantId),
        eq(sessionConnectorGrants.organizationId, input.organizationId),
        eq(sessionConnectorGrants.conversationId, input.conversationId),
        eq(connectorAuthorizations.organizationId, input.organizationId)
      )
    );

  if (!row) {
    return null;
  }

  if (row.auth.principalId !== input.callerPrincipalId && !input.allowManageOthers) {
    throw APIError.permissionDenied(
      "connector authorization belongs to another principal (authorization owner mismatch)"
    );
  }

  const [updated] = await db
    .update(sessionConnectorGrants)
    .set({
      state: "revoked",
      revokedAt: new Date(),
      updatedAt: new Date(),
    })
    .where(eq(sessionConnectorGrants.id, row.grant.id))
    .returning();

  return updated || null;
}

export async function assertConnectorInvocation(input: {
  organizationId: string;
  conversationId: string;
  connectorKey: string;
  action?: string;
  requiredScope?: string;
}): Promise<{ ok: boolean; secretRef?: string; error?: string }> {
  // Join session grant -> authorization -> installation
  const rows = await db
    .select({
      grant: sessionConnectorGrants,
      auth: connectorAuthorizations,
      inst: workspaceConnectorInstallations,
    })
    .from(sessionConnectorGrants)
    .innerJoin(connectorAuthorizations, eq(sessionConnectorGrants.authorizationId, connectorAuthorizations.id))
    .innerJoin(workspaceConnectorInstallations, eq(connectorAuthorizations.installationId, workspaceConnectorInstallations.id))
    .where(
      and(
        eq(sessionConnectorGrants.organizationId, input.organizationId),
        eq(sessionConnectorGrants.conversationId, input.conversationId),
        eq(workspaceConnectorInstallations.connectorKey, input.connectorKey)
      )
    );

  if (rows.length === 0) {
    return { ok: false, error: "connector_not_granted_to_session" };
  }

  const { grant, auth, inst } = rows[0];

  if (inst.status !== "enabled") {
    return { ok: false, error: "connector_installation_disabled" };
  }

  const now = new Date();

  if (auth.state !== "active" || auth.expiresAt < now) {
    return { ok: false, error: "connector_reauth_required" };
  }

  if (grant.state !== "enabled" || (grant.expiresAt && grant.expiresAt < now)) {
    return { ok: false, error: "connector_reauth_required" };
  }

  if (input.requiredScope) {
    const scopes = (auth.grantedScopes as string[]) || [];
    if (!scopes.includes(input.requiredScope)) {
      return { ok: false, error: "connector_scope_missing" };
    }
  }

  if (input.action) {
    const actions = (grant.allowedActions as string[]) || [];
    if (actions.length > 0 && !actions.includes(input.action)) {
      return { ok: false, error: "connector_action_not_allowed" };
    }
  }

  return { ok: true, secretRef: auth.secretRef };
}
