import { and, desc, eq, sql } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../db";
import {
  profiles,
  users,
  workspaceMemberships,
  workspaceSettingsAuditEvents,
  workspaceSkillPolicies,
} from "../storage/schema";
import {
  workspaceConnectorInstallations,
  workspaceRuntimeNodes,
} from "../storage/control-plane-schema";
import { extractAuthContext } from "../middleware";
import { listWorkspaceRuntimeNodes as listRegisteredRuntimeNodes } from "./runtime-node-registry.service";

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

async function verifyWorkspaceMembershipRow(authorization: string | undefined, workspaceId: string) {
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
    throw APIError.permissionDenied("user does not have permission to access this workspace");
  }

  return { actorId: authCtx.userID, membership: mem[0] };
}

async function verifyWorkspaceMembership(authorization: string | undefined, workspaceId: string): Promise<string> {
  const { actorId } = await verifyWorkspaceMembershipRow(authorization, workspaceId);
  return actorId;
}

// Task 4 — quyết định mutate skill policy chỉ dành cho workspace operator
// (founder/co-founder/admin), khớp `_WORKSPACE_OPERATOR_ROLES` phía Python
// (apps/cosa/auth/dependency.py::require_workspace_operator) để 2 phía đồng
// nhất khái niệm "operator" dù kiểm tra ở 2 tầng khác nhau.
const WORKSPACE_OPERATOR_ROLES = new Set(["founder", "co-founder", "admin"]);

async function requireWorkspaceOperator(authorization: string | undefined, workspaceId: string): Promise<string> {
  const { actorId, membership } = await verifyWorkspaceMembershipRow(authorization, workspaceId);
  if (!WORKSPACE_OPERATOR_ROLES.has((membership.roleId || "").toLowerCase())) {
    throw APIError.permissionDenied("workspace operator role required");
  }
  return actorId;
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

// ─── Session Context (Task 3 — Frontend Trust and UX Hardening) ───
//
// Nguồn sự thật DUY NHẤT cho "workspace/role/runtimeMode/presence hiện tại
// của phiên đăng nhập" phải nằm ở server: Flutter tuyệt đối không được coi
// runtimeMode/role/presence do CHÍNH NÓ gửi lên là một assertion bảo mật.
// Endpoint chỉ nhận workspaceId (path) + Authorization — không nhận
// runtimeMode/role/presence trong body/query — mọi giá trị trả về đều được
// tính lại từ dữ liệu server (membership row + heartbeat thật).
export interface WorkspaceSessionContextView {
  readonly workspaceId: string;
  readonly role: string;
  readonly runtimeMode: "LOCAL_ONLY" | "REMOTE_ACCESS" | "CLOUD_CONTINUITY";
  readonly presenceStatus: "ONLINE" | "DEGRADED" | "OFFLINE";
  readonly lastHeartbeatAt: string | null;
  readonly asOf: string;
  readonly capabilities: readonly string[];
}

// Bộ capability tối thiểu suy ra từ role — mọi member đọc được session context
// của chính mình; chỉ operator (founder/co-founder/admin, cùng định nghĩa với
// `WORKSPACE_OPERATOR_ROLES` ở trên) mới có thêm quyền quản trị workspace.
const BASE_WORKSPACE_CAPABILITIES: readonly string[] = ["workspace.session.read"];
const OPERATOR_WORKSPACE_CAPABILITIES: readonly string[] = [
  "workspace.settings.manage",
  "workspace.skill_policy.manage",
  "workspace.runtime_node.manage",
];

function deriveWorkspaceCapabilities(roleId: string): readonly string[] {
  if (WORKSPACE_OPERATOR_ROLES.has((roleId || "").toLowerCase())) {
    return [...BASE_WORKSPACE_CAPABILITIES, ...OPERATOR_WORKSPACE_CAPABILITIES];
  }
  return BASE_WORKSPACE_CAPABILITIES;
}

// runtimeMode canonical thật sự nằm ở cột `runtime_mode` phía
// `services/company` (identity.workspaces) — cosa control-plane CHƯA có
// adapter cross-service đọc cột đó (đúng khoảng trống đã ghi chú tại
// `runtime-node.handler.ts` — "adapter cross-service để phiên sau"). Trong
// lúc chờ adapter đó, suy ra runtimeMode từ chính runtime node control-plane
// mà cosa đang sở hữu thật (bảng `workspace_runtime_nodes`), theo ĐÚNG state
// machine đã được test ở `runtime-router.service.ts`:
//   - có cloud node (chưa revoke)                  → CLOUD_CONTINUITY
//   - chỉ có local node, presence hiệu lực ONLINE   → LOCAL_ONLY
//   - chỉ có local node, presence hiệu lực khác     → REMOTE_ACCESS (đang cố
//     truy cập từ xa; guardrail 7 — KHÔNG được âm thầm failover cloud khi
//     chưa có cloud node nào đăng ký)
//   - chưa đăng ký node nào                         → LOCAL_ONLY mặc định,
//     presence OFFLINE (chưa có runtime nào để kết nối)
async function resolveWorkspaceRuntimeSnapshot(workspaceId: bigint): Promise<{
  runtimeMode: WorkspaceSessionContextView["runtimeMode"];
  presenceStatus: WorkspaceSessionContextView["presenceStatus"];
  lastHeartbeatAt: string | null;
}> {
  const nodes = await listRegisteredRuntimeNodes(workspaceId);
  const local = nodes.find((n) => n.runtimeRole === "local_workspace_runtime") ?? null;
  const cloud = nodes.find((n) => n.runtimeRole === "cloud_workspace_runtime") ?? null;

  if (cloud) {
    // CLOUD_CONTINUITY ưu tiên local khi local còn sống, khớp
    // `resolveRuntimeRoute` — chỉ dùng cloud khi local thật sự không online.
    const preferLocal = local !== null && local.presence !== "OFFLINE";
    const active = preferLocal ? (local as NonNullable<typeof local>) : cloud;
    return {
      runtimeMode: "CLOUD_CONTINUITY",
      presenceStatus: active.presence,
      lastHeartbeatAt: active.lastHeartbeatAt,
    };
  }

  if (local) {
    return {
      runtimeMode: local.presence === "ONLINE" ? "LOCAL_ONLY" : "REMOTE_ACCESS",
      presenceStatus: local.presence,
      lastHeartbeatAt: local.lastHeartbeatAt,
    };
  }

  return { runtimeMode: "LOCAL_ONLY", presenceStatus: "OFFLINE", lastHeartbeatAt: null };
}

export async function getWorkspaceSessionContextService(
  workspaceId: string,
  authorization?: string
): Promise<WorkspaceSessionContextView> {
  const { membership } = await verifyWorkspaceMembershipRow(authorization, workspaceId);
  const wsIdBigInt = BigInt(workspaceId);

  const { runtimeMode, presenceStatus, lastHeartbeatAt } = await resolveWorkspaceRuntimeSnapshot(wsIdBigInt);

  return {
    workspaceId,
    role: membership.roleId,
    runtimeMode,
    presenceStatus,
    lastHeartbeatAt,
    asOf: new Date().toISOString(),
    capabilities: deriveWorkspaceCapabilities(membership.roleId),
  };
}

// ─── Skill Policies (Task 4 — Truthful MVP Hardening) ───

export interface WorkspaceSkillPolicyView {
  readonly workspaceId: string;
  readonly skillKey: string;
  readonly enabled: boolean;
  readonly config: Record<string, unknown>;
  readonly revision: number;
  readonly updatedBy: string;
  readonly updatedAt: string;
}

export async function listWorkspaceSkillPoliciesService(
  workspaceId: string,
  authorization?: string
): Promise<MvpSuccess<readonly WorkspaceSkillPolicyView[]>> {
  await verifyWorkspaceMembership(authorization, workspaceId);
  const wsIdBigInt = BigInt(workspaceId);

  const rows = await db
    .select()
    .from(workspaceSkillPolicies)
    .where(eq(workspaceSkillPolicies.workspaceId, wsIdBigInt))
    .orderBy(desc(workspaceSkillPolicies.updatedAt));

  const items: WorkspaceSkillPolicyView[] = rows.map((r) => ({
    workspaceId: r.workspaceId.toString(),
    skillKey: r.skillKey,
    enabled: r.enabled,
    config: (r.config as Record<string, unknown>) ?? {},
    revision: r.revision,
    updatedBy: r.updatedBy,
    updatedAt: r.updatedAt.toISOString(),
  }));

  return mvpList(items, [SOURCE_CONTROL_PLANE]);
}

export async function putWorkspaceSkillPolicyService(
  workspaceId: string,
  skillKey: string,
  enabled: boolean,
  config: Record<string, unknown>,
  authorization?: string
): Promise<MvpSuccess<WorkspaceSkillPolicyView>> {
  // Chỉ workspace operator (founder/co-founder/admin) được mutate policy —
  // member thường chỉ được đọc (list ở trên chỉ yêu cầu membership).
  const actorId = await requireWorkspaceOperator(authorization, workspaceId);
  const wsIdBigInt = BigInt(workspaceId);

  // Upsert + audit event trong CÙNG 1 transaction — không được ghi policy mà
  // thiếu audit event tương ứng (và ngược lại).
  const saved = await db.transaction(async (tx) => {
    const [row] = await tx
      .insert(workspaceSkillPolicies)
      .values({
        workspaceId: wsIdBigInt,
        skillKey,
        enabled,
        config,
        revision: 1,
        updatedBy: actorId,
      })
      .onConflictDoUpdate({
        target: [workspaceSkillPolicies.workspaceId, workspaceSkillPolicies.skillKey],
        set: {
          enabled,
          config,
          revision: sql`${workspaceSkillPolicies.revision} + 1`,
          updatedBy: actorId,
          updatedAt: new Date(),
        },
      })
      .returning();

    await tx.insert(workspaceSettingsAuditEvents).values({
      eventId: BigInt(Date.now()) * 1000n + BigInt(Math.floor(Math.random() * 1000)),
      workspaceId: wsIdBigInt,
      actorId,
      eventType: "skill_policy.updated",
      targetKind: "skill_policy",
      targetId: skillKey,
      details: { skillKey, enabled, revision: row.revision },
    });

    return row;
  });

  const out: WorkspaceSkillPolicyView = {
    workspaceId: saved.workspaceId.toString(),
    skillKey: saved.skillKey,
    enabled: saved.enabled,
    config: (saved.config as Record<string, unknown>) ?? {},
    revision: saved.revision,
    updatedBy: saved.updatedBy,
    updatedAt: saved.updatedAt.toISOString(),
  };

  return mvpItem(out, [SOURCE_CONTROL_PLANE]);
}
