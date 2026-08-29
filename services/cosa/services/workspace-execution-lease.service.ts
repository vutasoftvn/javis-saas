// M6 §2 — WorkspaceExecutionLease + fencing (split-brain protection).
//
// Mỗi workspace CHỈ MỘT write-authoritative runtime tại một thời điểm. Mọi durable
// write / run completion phải kèm `fencing_token`; store gọi
// `assertFencingTokenCurrent` để từ chối write mang token của epoch cũ.
//
// - Local reclaim: `acquireWriteLease` (role local) — lease hết hạn ⇒ epoch+1 + token mới.
// - Cloud promote: `promoteCloudRuntime` — CHỈ khi local lease hết hạn VÀ sync
//   freshness đạt policy VÀ `failover_policy != MANUAL` (finance/legal mặc định MANUAL).
// - Local quay lại sau khi cloud đã ghi ⇒ `acquireWriteLease` cấp epoch mới; token
//   cũ của cloud từ đó bị `assertFencingTokenCurrent` reject.
import { APIError } from "encore.dev/api";
import { eq, sql } from "drizzle-orm";
import { db, schema } from "../models/db";

const { workspaceExecutionLeases } = schema;

export type RuntimeRole = "local_workspace_runtime" | "cloud_workspace_runtime";
export type FailoverPolicy = "AUTO" | "MANUAL";
export type SyncFreshness = "FRESH" | "STALE" | "UNKNOWN";

export const DEFAULT_LEASE_TTL_SEC = 60;

export interface WriteLeaseView {
  workspaceId: string;
  activeRuntimeNodeId: string;
  activeRuntimeRole: RuntimeRole;
  leaseEpoch: string;
  fencingToken: string;
  leaseExpiresAt: string;
  lastHeartbeatAt: string;
  lastSyncCursor: string | null;
  failoverPolicy: FailoverPolicy;
  isExpired: boolean;
}

type LeaseRow = typeof workspaceExecutionLeases.$inferSelect;

function toView(row: LeaseRow, now: Date = new Date()): WriteLeaseView {
  return {
    workspaceId: row.workspaceId.toString(),
    activeRuntimeNodeId: row.activeRuntimeNodeId.toString(),
    activeRuntimeRole: row.activeRuntimeRole as RuntimeRole,
    leaseEpoch: row.leaseEpoch.toString(),
    fencingToken: row.fencingToken.toString(),
    leaseExpiresAt: row.leaseExpiresAt.toISOString(),
    lastHeartbeatAt: row.lastHeartbeatAt.toISOString(),
    lastSyncCursor: row.lastSyncCursor,
    failoverPolicy: row.failoverPolicy as FailoverPolicy,
    isExpired: row.leaseExpiresAt <= now,
  };
}

type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];

async function nextFencingToken(tx: Tx): Promise<bigint> {
  const res = (await tx.execute(
    sql`SELECT nextval('control_plane.workspace_execution_fencing_seq') AS nextval`
  )) as unknown as { rows: Array<{ nextval: string }> };
  return BigInt(res.rows[0].nextval);
}

async function grantLease(
  tx: Tx,
  params: {
    workspaceId: bigint;
    nodeId: bigint;
    role: RuntimeRole;
    ttlSec: number;
    failoverPolicy?: FailoverPolicy;
    existing: LeaseRow | undefined;
    now: Date;
  }
): Promise<WriteLeaseView> {
  const { workspaceId, nodeId, role, ttlSec, existing, now } = params;
  const expiresAt = new Date(now.getTime() + ttlSec * 1000);
  const epoch = existing ? existing.leaseEpoch + 1n : 1n;
  const fencing = await nextFencingToken(tx);
  const failover = params.failoverPolicy ?? (existing?.failoverPolicy as FailoverPolicy) ?? "AUTO";

  if (existing) {
    const [updated] = await tx
      .update(workspaceExecutionLeases)
      .set({
        activeRuntimeNodeId: nodeId,
        activeRuntimeRole: role,
        leaseEpoch: epoch,
        fencingToken: fencing,
        leaseExpiresAt: expiresAt,
        lastHeartbeatAt: now,
        failoverPolicy: failover,
        updatedAt: now,
      })
      .where(eq(workspaceExecutionLeases.workspaceId, workspaceId))
      .returning();
    return toView(updated, now);
  }

  const [created] = await tx
    .insert(workspaceExecutionLeases)
    .values({
      workspaceId,
      activeRuntimeNodeId: nodeId,
      activeRuntimeRole: role,
      leaseEpoch: epoch,
      fencingToken: fencing,
      leaseExpiresAt: expiresAt,
      lastHeartbeatAt: now,
      failoverPolicy: failover,
    })
    .returning();
  return toView(created, now);
}

export interface AcquireWriteLeaseParams {
  workspaceId: bigint;
  nodeId: bigint;
  runtimeRole?: RuntimeRole; // mặc định local
  ttlSec?: number;
  failoverPolicy?: FailoverPolicy;
}

/**
 * Lấy / gia hạn write lease cho local runtime.
 *  - chưa có lease ⇒ cấp epoch 1.
 *  - đang giữ bởi CHÍNH node này & còn hạn ⇒ gia hạn tại chỗ (epoch/token KHÔNG đổi).
 *  - giữ bởi node KHÁC & còn hạn ⇒ FAILED_PRECONDITION (không cướp lease đang sống).
 *  - giữ bởi node khác & HẾT HẠN ⇒ tiếp quản với epoch+1 + fencing token mới.
 * Cloud runtime KHÔNG dùng hàm này — phải qua `promoteCloudRuntime`.
 */
export async function acquireWriteLease(p: AcquireWriteLeaseParams): Promise<WriteLeaseView> {
  const role: RuntimeRole = p.runtimeRole ?? "local_workspace_runtime";
  if (role === "cloud_workspace_runtime") {
    throw APIError.invalidArgument("cloud runtime phải dùng promoteCloudRuntime");
  }
  const ttl = p.ttlSec ?? DEFAULT_LEASE_TTL_SEC;

  return db.transaction(async (tx) => {
    const now = new Date();
    const [existing] = await tx
      .select()
      .from(workspaceExecutionLeases)
      .where(eq(workspaceExecutionLeases.workspaceId, p.workspaceId))
      .for("update");

    if (existing && existing.leaseExpiresAt > now) {
      if (existing.activeRuntimeNodeId === p.nodeId) {
        const expiresAt = new Date(now.getTime() + ttl * 1000);
        const [renewed] = await tx
          .update(workspaceExecutionLeases)
          .set({ leaseExpiresAt: expiresAt, lastHeartbeatAt: now, updatedAt: now })
          .where(eq(workspaceExecutionLeases.workspaceId, p.workspaceId))
          .returning();
        return toView(renewed, now);
      }
      throw APIError.failedPrecondition(
        `write lease đang giữ bởi runtime '${existing.activeRuntimeNodeId}' (epoch ${existing.leaseEpoch}) tới ${existing.leaseExpiresAt.toISOString()}`
      );
    }

    return grantLease(tx, {
      workspaceId: p.workspaceId,
      nodeId: p.nodeId,
      role,
      ttlSec: ttl,
      failoverPolicy: p.failoverPolicy,
      existing,
      now,
    });
  });
}

export interface PromoteCloudParams {
  workspaceId: bigint;
  cloudNodeId: bigint;
  syncFreshness: SyncFreshness;
  ttlSec?: number;
}

/**
 * Promote cloud runtime. CHỈ thành công khi:
 *  - đã có lease và lease đó HẾT HẠN (local lease hết hạn), VÀ
 *  - `failover_policy != MANUAL`, VÀ
 *  - `syncFreshness === 'FRESH'` (STALE/UNKNOWN ⇒ từ chối — không chạy trên state cũ).
 */
export async function promoteCloudRuntime(p: PromoteCloudParams): Promise<WriteLeaseView> {
  const ttl = p.ttlSec ?? DEFAULT_LEASE_TTL_SEC;

  return db.transaction(async (tx) => {
    const now = new Date();
    const [existing] = await tx
      .select()
      .from(workspaceExecutionLeases)
      .where(eq(workspaceExecutionLeases.workspaceId, p.workspaceId))
      .for("update");

    if (!existing) {
      throw APIError.failedPrecondition(
        "workspace chưa có execution lease — local runtime phải acquire trước khi cloud có thể promote"
      );
    }
    if (existing.leaseExpiresAt > now) {
      throw APIError.failedPrecondition(
        `local lease vẫn còn hiệu lực tới ${existing.leaseExpiresAt.toISOString()} — không promote cloud`
      );
    }
    if (existing.failoverPolicy === "MANUAL") {
      throw APIError.failedPrecondition(
        "failover_policy=MANUAL (finance/legal) — promote cloud phải do người quyết định"
      );
    }
    if (p.syncFreshness !== "FRESH") {
      throw APIError.failedPrecondition(
        `sync freshness '${p.syncFreshness}' chưa đạt policy — không promote cloud trên state cũ`
      );
    }

    return grantLease(tx, {
      workspaceId: p.workspaceId,
      nodeId: p.cloudNodeId,
      role: "cloud_workspace_runtime",
      ttlSec: ttl,
      existing,
      now,
    });
  });
}

export interface FencingCheckResult {
  workspaceId: string;
  leaseEpoch: string;
  fencingToken: string;
  activeRuntimeNodeId: string;
}

/**
 * Cổng cho mọi durable write: từ chối write mang fencing token != token hiện hành.
 * Token cũ (epoch trước) ⇒ ABORTED (split-brain — writer đã bị fenced).
 */
export async function assertFencingTokenCurrent(p: {
  workspaceId: bigint;
  fencingToken: bigint;
}): Promise<FencingCheckResult> {
  const [row] = await db
    .select()
    .from(workspaceExecutionLeases)
    .where(eq(workspaceExecutionLeases.workspaceId, p.workspaceId));

  if (!row) {
    throw APIError.failedPrecondition("workspace chưa có execution lease");
  }
  if (row.fencingToken !== p.fencingToken) {
    throw APIError.aborted(
      `fencing token ${p.fencingToken} không phải token hiện hành (${row.fencingToken}, epoch ${row.leaseEpoch}) — write bị từ chối (split-brain protection)`
    );
  }
  return {
    workspaceId: row.workspaceId.toString(),
    leaseEpoch: row.leaseEpoch.toString(),
    fencingToken: row.fencingToken.toString(),
    activeRuntimeNodeId: row.activeRuntimeNodeId.toString(),
  };
}

export async function heartbeatWriteLease(p: {
  workspaceId: bigint;
  nodeId: bigint;
  fencingToken: bigint;
  ttlSec?: number;
  syncCursor?: string;
}): Promise<WriteLeaseView> {
  const ttl = p.ttlSec ?? DEFAULT_LEASE_TTL_SEC;
  return db.transaction(async (tx) => {
    const now = new Date();
    const [row] = await tx
      .select()
      .from(workspaceExecutionLeases)
      .where(eq(workspaceExecutionLeases.workspaceId, p.workspaceId))
      .for("update");

    if (!row) throw APIError.notFound("không có execution lease cho workspace này");
    if (row.activeRuntimeNodeId !== p.nodeId || row.fencingToken !== p.fencingToken) {
      throw APIError.aborted("heartbeat với node/fencing token không hiện hành — đã bị fenced");
    }

    const [updated] = await tx
      .update(workspaceExecutionLeases)
      .set({
        leaseExpiresAt: new Date(now.getTime() + ttl * 1000),
        lastHeartbeatAt: now,
        lastSyncCursor: p.syncCursor ?? row.lastSyncCursor,
        updatedAt: now,
      })
      .where(eq(workspaceExecutionLeases.workspaceId, p.workspaceId))
      .returning();
    return toView(updated, now);
  });
}

export async function releaseWriteLease(p: {
  workspaceId: bigint;
  nodeId: bigint;
  fencingToken: bigint;
}): Promise<void> {
  await db.transaction(async (tx) => {
    const [row] = await tx
      .select()
      .from(workspaceExecutionLeases)
      .where(eq(workspaceExecutionLeases.workspaceId, p.workspaceId))
      .for("update");
    if (!row) return;
    if (row.activeRuntimeNodeId !== p.nodeId || row.fencingToken !== p.fencingToken) {
      throw APIError.aborted("release với node/fencing token không hiện hành");
    }
    // Đánh dấu hết hạn ngay (giữ row để lịch sử epoch + cho lần acquire kế tiếp bump epoch).
    await tx
      .update(workspaceExecutionLeases)
      .set({ leaseExpiresAt: new Date(0), updatedAt: new Date() })
      .where(eq(workspaceExecutionLeases.workspaceId, p.workspaceId));
  });
}

export async function setFailoverPolicy(p: {
  workspaceId: bigint;
  policy: FailoverPolicy;
}): Promise<void> {
  await db
    .update(workspaceExecutionLeases)
    .set({ failoverPolicy: p.policy, updatedAt: new Date() })
    .where(eq(workspaceExecutionLeases.workspaceId, p.workspaceId));
}

export async function getWriteLease(workspaceId: bigint): Promise<WriteLeaseView | null> {
  const [row] = await db
    .select()
    .from(workspaceExecutionLeases)
    .where(eq(workspaceExecutionLeases.workspaceId, workspaceId));
  return row ? toView(row) : null;
}
