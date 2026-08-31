import { and, desc, eq } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../db";
import {
  profiles,
  users,
  workspaceMemberships,
  workspaceSettingsAuditEvents,
} from "../storage/schema";
import {
  workspaceConnectorInstallations,
  workspaceRuntimeNodes,
} from "../storage/control-plane-schema";
import { extractAuthContext } from "../middleware";

export interface MvpSourceRef {
  readonly kind: "company_db" | "agent_db" | "object_store" | "control_plane" | "external_connector";
  readonly ref: string;
  readonly observedAt?: string;
}

export interface MvpSuccess<T> {
  readonly data: T;
  readonly meta: {
    readonly dataState: "populated" | "empty";
    readonly observedAt: string;
    readonly sources: readonly MvpSourceRef[];
  };
}

function mvpList<T>(items: readonly T[], sources: readonly MvpSourceRef[]): MvpSuccess<readonly T[]> {
  return {
    data: items,
    meta: {
      dataState: items.length > 0 ? "populated" : "empty",
      observedAt: new Date().toISOString(),
      sources,
    },
  };
}

function mvpItem<T>(item: T, sources: readonly MvpSourceRef[]): MvpSuccess<T> {
  return {
    data: item,
    meta: {
      dataState: "populated",
      observedAt: new Date().toISOString(),
      sources,
    },
  };
}

const SOURCE_CONTROL_PLANE: MvpSourceRef = { kind: "control_plane", ref: "control_plane.settings" };

async function verifyWorkspaceMembership(authorization: string | undefined, workspaceId: string): Promise<string> {
  const authCtx = extractAuthContext(authorization, workspaceId);

  const wsIdBigInt = BigInt(workspaceId);
  const userIdBigInt = BigInt(authCtx.userID);

  const mem = await db
    .select()
    .from(workspaceMemberships)
    .where(and(eq(workspaceMemberships.workspaceId, wsIdBigInt), eq(workspaceMemberships.userId, userIdBigInt)))
    .limit(1);

  if (mem.length === 0) {
    // If not a member, check if user is admin or throw permissionDenied
    throw APIError.permissionDenied("user does not belong to this workspace");
  }

  return authCtx.userID;
}

// ─── Members ───

export interface WorkspaceMemberDTO {
  readonly id: string;
  readonly workspaceId: string;
  readonly userId: string;
  readonly roleId: string;
  readonly email: string | null;
  readonly fullName: string | null;
  readonly createdAt: string;
}

export async function listWorkspaceMembersService(
  workspaceId: string,
  authorization?: string
): Promise<MvpSuccess<readonly WorkspaceMemberDTO[]>> {
  await verifyWorkspaceMembership(authorization, workspaceId);
  const wsIdBigInt = BigInt(workspaceId);

  const rows = await db
    .select({
      mem: workspaceMemberships,
      u: users,
      p: profiles,
    })
    .from(workspaceMemberships)
    .innerJoin(users, eq(workspaceMemberships.userId, users.id))
    .leftJoin(profiles, eq(users.id, profiles.id))
    .where(eq(workspaceMemberships.workspaceId, wsIdBigInt));

  const items: WorkspaceMemberDTO[] = rows.map(({ mem, u, p }) => ({
    id: mem.id.toString(),
    workspaceId: mem.workspaceId.toString(),
    userId: mem.userId.toString(),
    roleId: mem.roleId,
    email: u.email,
    fullName: p?.fullName ?? null,
    createdAt: mem.createdAt.toISOString(),
  }));

  return mvpList(items, [SOURCE_CONTROL_PLANE]);
}

// ─── Connectors ───

export interface ConnectorStatusView {
  readonly id: string;
  readonly connectorKey: string;
  readonly state: "not_connected" | "enabled" | "expired" | "revoked" | "unavailable";
  readonly grantedScopes: readonly string[];
  readonly observedAt: string | null;
  readonly expiresAt: string | null;
  readonly reason: string | null;
}

export async function listWorkspaceConnectorsService(
  workspaceId: string,
  authorization?: string
): Promise<MvpSuccess<readonly ConnectorStatusView[]>> {
  await verifyWorkspaceMembership(authorization, workspaceId);

  const rows = await db
    .select()
    .from(workspaceConnectorInstallations)
    .where(eq(workspaceConnectorInstallations.workspaceId, workspaceId));

  const items: ConnectorStatusView[] = rows.map((r) => ({
    id: r.id,
    connectorKey: r.connectorKey,
    state: (r.status === "installed" ? "enabled" : r.status) as any,
    grantedScopes: [],
    observedAt: r.createdAt?.toISOString() ?? null,
    expiresAt: null,
    reason: null,
  }));

  return mvpList(items, [SOURCE_CONTROL_PLANE]);
}

export async function installWorkspaceConnectorService(
  workspaceId: string,
  connectorKey: string,
  authorization?: string
): Promise<MvpSuccess<ConnectorStatusView>> {
  const actorId = await verifyWorkspaceMembership(authorization, workspaceId);

  const id = `conn_${Date.now()}`;
  const now = new Date();

  await db
    .insert(workspaceConnectorInstallations)
    .values({
      id,
      workspaceId,
      connectorKey,
      installedBy: actorId,
      status: "enabled",
      createdAt: now,
      updatedAt: now,
    })
    .onConflictDoUpdate({
      target: [workspaceConnectorInstallations.workspaceId, workspaceConnectorInstallations.connectorKey],
      set: {
        status: "enabled",
        updatedAt: now,
      },
    });

  // Audit log
  await db.insert(workspaceSettingsAuditEvents).values({
    eventId: BigInt(Date.now()),
    workspaceId: BigInt(workspaceId),
    actorId,
    eventType: "connector.installed",
    targetKind: "connector",
    targetId: connectorKey,
    details: { connectorKey, status: "enabled" },
  });

  const out: ConnectorStatusView = {
    id,
    connectorKey,
    state: "enabled",
    grantedScopes: ["read", "write"],
    observedAt: now.toISOString(),
    expiresAt: null,
    reason: null,
  };
  return mvpItem(out, [SOURCE_CONTROL_PLANE]);
}

export async function revokeWorkspaceConnectorService(
  workspaceId: string,
  connectorKey: string,
  authorization?: string
): Promise<MvpSuccess<ConnectorStatusView>> {
  const actorId = await verifyWorkspaceMembership(authorization, workspaceId);
  const now = new Date();

  await db
    .update(workspaceConnectorInstallations)
    .set({ status: "disabled", updatedAt: now })
    .where(
      and(
        eq(workspaceConnectorInstallations.workspaceId, workspaceId),
        eq(workspaceConnectorInstallations.connectorKey, connectorKey)
      )
    );

  // Audit log
  await db.insert(workspaceSettingsAuditEvents).values({
    eventId: BigInt(Date.now()),
    workspaceId: BigInt(workspaceId),
    actorId,
    eventType: "connector.revoked",
    targetKind: "connector",
    targetId: connectorKey,
    details: { connectorKey, status: "revoked" },
  });

  const out: ConnectorStatusView = {
    id: `conn_${connectorKey}`,
    connectorKey,
    state: "revoked",
    grantedScopes: [],
    observedAt: now.toISOString(),
    expiresAt: null,
    reason: "revoked_by_user",
  };
  return mvpItem(out, [SOURCE_CONTROL_PLANE]);
}

// ─── Runtime Nodes ───

export interface RuntimeNodeView {
  readonly id: string;
  readonly workspaceId: string;
  readonly nodeId: string;
  readonly runtimeRole: string;
  readonly presence: "ONLINE" | "OFFLINE" | "DEGRADED";
  readonly lastHeartbeatAt: string | null;
  readonly status: string;
}

export async function listWorkspaceRuntimeNodesService(
  workspaceId: string,
  authorization?: string
): Promise<MvpSuccess<readonly RuntimeNodeView[]>> {
  await verifyWorkspaceMembership(authorization, workspaceId);
  const wsIdBigInt = BigInt(workspaceId);

  const rows = await db
    .select()
    .from(workspaceRuntimeNodes)
    .where(eq(workspaceRuntimeNodes.workspaceId, wsIdBigInt));

  const now = Date.now();
  const items: RuntimeNodeView[] = rows.map((r) => {
    const lastHb = r.lastHeartbeatAt ? r.lastHeartbeatAt.getTime() : 0;
    const isOnline = now - lastHb < 60000; // online if heartbeat within 60s
    const isRevoked = r.revokedAt !== null;
    const status = isRevoked ? "revoked" : (r.presenceStatus || "active");
    return {
      id: r.nodeId.toString(),
      workspaceId: r.workspaceId.toString(),
      nodeId: r.nodeId.toString(),
      runtimeRole: r.runtimeRole,
      presence: isOnline ? "ONLINE" : "OFFLINE",
      lastHeartbeatAt: r.lastHeartbeatAt?.toISOString() ?? null,
      status,
    };
  });

  return mvpList(items, [SOURCE_CONTROL_PLANE]);
}

export async function revokeWorkspaceRuntimeNodeService(
  workspaceId: string,
  nodeId: string,
  authorization?: string
): Promise<MvpSuccess<{ revoked: boolean }>> {
  const actorId = await verifyWorkspaceMembership(authorization, workspaceId);
  const wsIdBigInt = BigInt(workspaceId);
  const nodeIdBigInt = BigInt(nodeId);

  await db
    .update(workspaceRuntimeNodes)
    .set({ revokedAt: new Date(), presenceStatus: "OFFLINE", updatedAt: new Date() })
    .where(and(eq(workspaceRuntimeNodes.workspaceId, wsIdBigInt), eq(workspaceRuntimeNodes.nodeId, nodeIdBigInt)));

  await db.insert(workspaceSettingsAuditEvents).values({
    eventId: BigInt(Date.now()),
    workspaceId: wsIdBigInt,
    actorId,
    eventType: "runtime_node.revoked",
    targetKind: "runtime_node",
    targetId: nodeId,
    details: { nodeId, status: "revoked" },
  });

  return mvpItem({ revoked: true }, [SOURCE_CONTROL_PLANE]);
}

// ─── Audit Events ───

export interface WorkspaceAuditEventDTO {
  readonly eventId: string;
  readonly workspaceId: string;
  readonly actorId: string;
  readonly eventType: string;
  readonly targetKind: string;
  readonly targetId: string;
  readonly details: unknown;
  readonly createdAt: string;
}

export async function listWorkspaceAuditEventsService(
  workspaceId: string,
  authorization?: string
): Promise<MvpSuccess<readonly WorkspaceAuditEventDTO[]>> {
  await verifyWorkspaceMembership(authorization, workspaceId);
  const wsIdBigInt = BigInt(workspaceId);

  const rows = await db
    .select()
    .from(workspaceSettingsAuditEvents)
    .where(eq(workspaceSettingsAuditEvents.workspaceId, wsIdBigInt))
    .orderBy(desc(workspaceSettingsAuditEvents.createdAt))
    .limit(100);

  const items: WorkspaceAuditEventDTO[] = rows.map((r) => ({
    eventId: r.eventId.toString(),
    workspaceId: r.workspaceId.toString(),
    actorId: r.actorId,
    eventType: r.eventType,
    targetKind: r.targetKind,
    targetId: r.targetId,
    details: r.details,
    createdAt: r.createdAt.toISOString(),
  }));

  return mvpList(items, [SOURCE_CONTROL_PLANE]);
}
