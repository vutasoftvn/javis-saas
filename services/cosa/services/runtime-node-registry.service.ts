// M5 §1 — Runtime node registration + device key + heartbeat + computed presence.
//
// Local Workspace Runtime Node đăng ký lúc khởi động với device_key_fingerprint
// (từ OS Keychain — reuse cơ chế M3 §6), rồi gửi heartbeat định kỳ. Node chưa
// đăng ký hoặc device key không khớp ⇒ KHÔNG được nhận command
// (`assertNodeMayReceiveCommand`).
//
// presence "hiệu lực" KHÔNG đọc thẳng cột `presence_status` (chỉ là last-known)
// mà tính lại theo độ tươi của `last_heartbeat_at` — vì `now()` không IMMUTABLE
// nên không thể để logic này trong index/generated column.
import { APIError } from "encore.dev/api";
import { and, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "./snowflake.service";

const { workspaceRuntimeNodes } = schema;

export type RuntimeRole = "local_workspace_runtime" | "cloud_workspace_runtime";
export type PresenceStatus = "ONLINE" | "OFFLINE" | "DEGRADED";

// Heartbeat tươi trong 45s ⇒ ONLINE; trong 120s ⇒ DEGRADED; quá ⇒ OFFLINE.
export const PRESENCE_ONLINE_WITHIN_SEC = 45;
export const PRESENCE_DEGRADED_WITHIN_SEC = 120;

const RUNTIME_ROLES: readonly RuntimeRole[] = [
  "local_workspace_runtime",
  "cloud_workspace_runtime",
];

export interface RuntimeNodeView {
  nodeId: string;
  workspaceId: string;
  deviceKeyFingerprint: string;
  runtimeRole: RuntimeRole;
  presence: PresenceStatus;
  agentVersion: string | null;
  lastHeartbeatAt: string | null;
  registeredAt: string;
  revokedAt: string | null;
}

export function computePresence(
  lastHeartbeatAt: Date | null,
  revokedAt: Date | null,
  now: Date = new Date()
): PresenceStatus {
  if (revokedAt || !lastHeartbeatAt) return "OFFLINE";
  const ageSec = (now.getTime() - lastHeartbeatAt.getTime()) / 1000;
  if (ageSec <= PRESENCE_ONLINE_WITHIN_SEC) return "ONLINE";
  if (ageSec <= PRESENCE_DEGRADED_WITHIN_SEC) return "DEGRADED";
  return "OFFLINE";
}

type NodeRow = typeof workspaceRuntimeNodes.$inferSelect;

function toView(row: NodeRow, now: Date = new Date()): RuntimeNodeView {
  return {
    nodeId: row.nodeId.toString(),
    workspaceId: row.workspaceId.toString(),
    deviceKeyFingerprint: row.deviceKeyFingerprint,
    runtimeRole: row.runtimeRole as RuntimeRole,
    presence: computePresence(row.lastHeartbeatAt, row.revokedAt, now),
    agentVersion: row.agentVersion,
    lastHeartbeatAt: row.lastHeartbeatAt ? row.lastHeartbeatAt.toISOString() : null,
    registeredAt: row.registeredAt.toISOString(),
    revokedAt: row.revokedAt ? row.revokedAt.toISOString() : null,
  };
}

function isUniqueViolation(err: unknown): boolean {
  let cur: unknown = err;
  for (let d = 0; d < 5 && cur; d++) {
    if (typeof cur === "object" && cur !== null) {
      const o = cur as { code?: string; message?: string; cause?: unknown };
      if (o.code === "23505") return true;
      if (typeof o.message === "string" && o.message.includes("duplicate key value")) return true;
      cur = o.cause;
    } else break;
  }
  return false;
}

export interface RegisterRuntimeNodeParams {
  workspaceId: bigint;
  deviceKeyFingerprint: string;
  runtimeRole: RuntimeRole;
  agentVersion?: string;
}

/**
 * Idempotent: `(workspace_id, device_key_fingerprint)` đang hoạt động ⇒ trả lại
 * đúng node cũ (chỉ refresh agent_version + heartbeat). Chưa có ⇒ tạo node mới
 * với node_id Snowflake do control-plane sinh.
 */
export async function registerRuntimeNode(
  p: RegisterRuntimeNodeParams
): Promise<RuntimeNodeView> {
  const fingerprint = p.deviceKeyFingerprint?.trim();
  if (!fingerprint) {
    throw APIError.invalidArgument("device_key_fingerprint là bắt buộc");
  }
  if (!RUNTIME_ROLES.includes(p.runtimeRole)) {
    throw APIError.invalidArgument(`runtime_role không hợp lệ: ${p.runtimeRole}`);
  }

  try {
    return await db.transaction(async (tx) => {
      const now = new Date();
      const [existing] = await tx
        .select()
        .from(workspaceRuntimeNodes)
        .where(
          and(
            eq(workspaceRuntimeNodes.workspaceId, p.workspaceId),
            eq(workspaceRuntimeNodes.deviceKeyFingerprint, fingerprint),
            isNull(workspaceRuntimeNodes.revokedAt)
          )
        )
        .for("update");

      if (existing) {
        const [updated] = await tx
          .update(workspaceRuntimeNodes)
          .set({
            agentVersion: p.agentVersion ?? existing.agentVersion,
            runtimeRole: p.runtimeRole,
            lastHeartbeatAt: now,
            presenceStatus: "ONLINE",
            updatedAt: now,
          })
          .where(eq(workspaceRuntimeNodes.nodeId, existing.nodeId))
          .returning();
        return toView(updated, now);
      }

      const [created] = await tx
        .insert(workspaceRuntimeNodes)
        .values({
          nodeId: generateSnowflake(),
          workspaceId: p.workspaceId,
          deviceKeyFingerprint: fingerprint,
          runtimeRole: p.runtimeRole,
          presenceStatus: "ONLINE",
          agentVersion: p.agentVersion ?? null,
          lastHeartbeatAt: now,
          registeredAt: now,
        })
        .returning();
      return toView(created, now);
    });
  } catch (err) {
    if (isUniqueViolation(err)) {
      // Đăng ký song song thắng cuộc đua — trả lại node đã tồn tại.
      const [row] = await db
        .select()
        .from(workspaceRuntimeNodes)
        .where(
          and(
            eq(workspaceRuntimeNodes.workspaceId, p.workspaceId),
            eq(workspaceRuntimeNodes.deviceKeyFingerprint, fingerprint),
            isNull(workspaceRuntimeNodes.revokedAt)
          )
        );
      if (row) return toView(row);
    }
    throw err;
  }
}

export interface HeartbeatParams {
  nodeId: bigint;
  workspaceId: bigint;
  deviceKeyFingerprint: string;
  agentVersion?: string;
}

export async function heartbeatRuntimeNode(p: HeartbeatParams): Promise<RuntimeNodeView> {
  const [row] = await db
    .select()
    .from(workspaceRuntimeNodes)
    .where(
      and(
        eq(workspaceRuntimeNodes.nodeId, p.nodeId),
        eq(workspaceRuntimeNodes.workspaceId, p.workspaceId)
      )
    );

  if (!row) throw APIError.notFound("runtime node không tồn tại");
  if (row.revokedAt) {
    throw APIError.permissionDenied("runtime node đã bị thu hồi — phải đăng ký lại");
  }
  if (row.deviceKeyFingerprint !== p.deviceKeyFingerprint?.trim()) {
    throw APIError.permissionDenied("device key fingerprint không khớp");
  }

  const now = new Date();
  const [updated] = await db
    .update(workspaceRuntimeNodes)
    .set({
      lastHeartbeatAt: now,
      presenceStatus: "ONLINE",
      agentVersion: p.agentVersion ?? row.agentVersion,
      updatedAt: now,
    })
    .where(eq(workspaceRuntimeNodes.nodeId, p.nodeId))
    .returning();
  return toView(updated, now);
}

export async function revokeRuntimeNode(p: {
  nodeId: bigint;
  workspaceId: bigint;
}): Promise<void> {
  const now = new Date();
  await db
    .update(workspaceRuntimeNodes)
    .set({ revokedAt: now, presenceStatus: "OFFLINE", updatedAt: now })
    .where(
      and(
        eq(workspaceRuntimeNodes.nodeId, p.nodeId),
        eq(workspaceRuntimeNodes.workspaceId, p.workspaceId),
        isNull(workspaceRuntimeNodes.revokedAt)
      )
    );
}

export async function listWorkspaceRuntimeNodes(
  workspaceId: bigint,
  opts: { includeRevoked?: boolean } = {}
): Promise<RuntimeNodeView[]> {
  const now = new Date();
  const rows = await db
    .select()
    .from(workspaceRuntimeNodes)
    .where(
      opts.includeRevoked
        ? eq(workspaceRuntimeNodes.workspaceId, workspaceId)
        : and(
            eq(workspaceRuntimeNodes.workspaceId, workspaceId),
            isNull(workspaceRuntimeNodes.revokedAt)
          )
    );
  return rows.map((r) => toView(r, now));
}

export interface CommandEligibility {
  nodeId: string;
  workspaceId: string;
  runtimeRole: RuntimeRole;
  presence: PresenceStatus;
}

/**
 * Cổng cho §3 Runtime Router / §4 command envelope: node phải đã đăng ký, chưa bị
 * thu hồi, device key khớp, và presence hiệu lực != OFFLINE. Sai bất kỳ điều kiện
 * nào ⇒ throw (KHÔNG phân biệt "không tồn tại" vs "sai key" để tránh lộ thông tin).
 */
export async function assertNodeMayReceiveCommand(p: {
  nodeId: bigint;
  workspaceId: bigint;
  deviceKeyFingerprint: string;
}): Promise<CommandEligibility> {
  const [row] = await db
    .select()
    .from(workspaceRuntimeNodes)
    .where(
      and(
        eq(workspaceRuntimeNodes.nodeId, p.nodeId),
        eq(workspaceRuntimeNodes.workspaceId, p.workspaceId)
      )
    );

  if (!row || row.revokedAt || row.deviceKeyFingerprint !== p.deviceKeyFingerprint?.trim()) {
    throw APIError.permissionDenied("runtime node chưa đăng ký hoặc device key không hợp lệ");
  }

  const presence = computePresence(row.lastHeartbeatAt, row.revokedAt);
  if (presence === "OFFLINE") {
    throw APIError.failedPrecondition("runtime node đang offline — không route command");
  }

  return {
    nodeId: row.nodeId.toString(),
    workspaceId: row.workspaceId.toString(),
    runtimeRole: row.runtimeRole as RuntimeRole,
    presence,
  };
}
