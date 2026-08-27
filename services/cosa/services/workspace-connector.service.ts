import { eq, and, sql } from "drizzle-orm";
import { db, schema } from "../models/db";

const {
  workspaceConnectorInstallations,
  connectorAuthorizations,
  sessionConnectorGrants,
} = schema;

export type ConnectorAuthorizationState = "active" | "expired" | "revoked";
export type SessionConnectorGrantState = "enabled" | "revoked" | "expired";

export function getAllowedConnectorKeys(): string[] {
  const envVal = process.env.COSA_CONNECTOR_ALLOWED_KEYS || "sandbox-read";
  return envVal.split(",").map((s) => s.trim()).filter(Boolean);
}

export function validateSecretRef(secretRef: string): void {
  if (!secretRef || !secretRef.startsWith("secret://cosa-connectors/")) {
    throw new Error("invalid secret_ref: must start with 'secret://cosa-connectors/'");
  }
}

export async function installWorkspaceConnector(input: {
  workspaceId: string;
  connectorKey: string;
  installedBy: string;
}) {
  const allowed = getAllowedConnectorKeys();
  if (!allowed.includes(input.connectorKey)) {
    throw new Error(`connector_key '${input.connectorKey}' is not allowed in current test capability set`);
  }

  const existing = await db
    .select()
    .from(workspaceConnectorInstallations)
    .where(
      and(
        eq(workspaceConnectorInstallations.workspaceId, input.workspaceId),
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
      workspaceId: input.workspaceId,
      connectorKey: input.connectorKey,
      installedBy: input.installedBy,
      status: "enabled",
    })
    .returning();

  return created;
}

export async function registerConnectorAuthorization(input: {
  installationId: string;
  workspaceId: string;
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
        eq(workspaceConnectorInstallations.workspaceId, input.workspaceId)
      )
    );

  if (!installation || installation.status !== "enabled") {
    throw new Error("installation not found or disabled");
  }

  const id = `conn_auth_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  const [created] = await db
    .insert(connectorAuthorizations)
    .values({
      id,
      installationId: input.installationId,
      workspaceId: input.workspaceId,
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
  workspaceId: string;
  conversationId: string;
  authorizationId: string;
  grantedBy: string;
  allowedActions: string[];
  expiresAt?: Date | null;
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
        eq(workspaceConnectorInstallations.workspaceId, input.workspaceId)
      )
    );

  if (!auth) {
    throw new Error("authorization not found or workspace mismatch");
  }

  const authRecord = auth.connector_authorizations;
  if (authRecord.state !== "active" || authRecord.expiresAt < new Date()) {
    throw new Error("connector_reauth_required: authorization is not active or has expired");
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
      workspaceId: input.workspaceId,
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
  workspaceId: string;
  conversationId: string;
  grantId: string;
}) {
  const [updated] = await db
    .update(sessionConnectorGrants)
    .set({
      state: "revoked",
      revokedAt: new Date(),
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(sessionConnectorGrants.id, input.grantId),
        eq(sessionConnectorGrants.workspaceId, input.workspaceId),
        eq(sessionConnectorGrants.conversationId, input.conversationId)
      )
    )
    .returning();

  return updated || null;
}

export async function assertConnectorInvocation(input: {
  workspaceId: string;
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
        eq(sessionConnectorGrants.workspaceId, input.workspaceId),
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
