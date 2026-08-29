// M2 §2 / ADR-ID-MODEL-001 — managed Snowflake generator slot registry.
//
// Chỉ generator authoritative (control-plane; cloud workspace runtime khi Cloud
// Continuity) lấy slot ở đây. `NODE_ID = Math.random()` bị bỏ. UNIQUE(slot) đảm
// bảo mỗi slot một row; "active" = lease_expires_at > now (kiểm ở service, vì
// now() không IMMUTABLE nên không dùng được trong partial index).
import { hostname } from "node:os";
import { APIError } from "encore.dev/api";
import { and, eq, gt, lte, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { configureGeneratorSlot } from "./snowflake.service";

const { snowflakeGeneratorSlots } = schema;

export const MAX_SLOT = 1023;
export const DEFAULT_LEASE_TTL_SEC = 60;

export type GeneratorRuntimeRole = "cosa_control_plane" | "cloud_workspace_runtime";

export interface GeneratorSlotLease {
  generatorId: string;
  slot: number;
  runtimeRole: GeneratorRuntimeRole;
  leaseEpoch: bigint;
  fencingToken: bigint;
  leaseExpiresAt: Date;
  clockCheckpoint: bigint;
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

async function nextFencingToken(tx: {
  execute: (q: unknown) => Promise<{ rows: Array<{ nextval: string }> }>;
}): Promise<bigint> {
  const res = await tx.execute(
    sql`SELECT nextval('control_plane.snowflake_fencing_seq') AS nextval`
  );
  return BigInt(res.rows[0].nextval);
}

/**
 * Lấy (hoặc gia hạn) slot cho `generatorId`. Nếu generator này đã có row:
 *  - lease còn hạn ⇒ gia hạn tại chỗ (giữ nguyên slot), epoch không đổi.
 *  - lease hết hạn ⇒ tái lấy slot đó với epoch+1 + fencing token mới.
 * Nếu chưa có row ⇒ tìm slot trống đầu tiên (0..1023). Không còn slot ⇒ FAILED_PRECONDITION.
 */
export async function acquireGeneratorSlot(params: {
  generatorId: string;
  runtimeRole: GeneratorRuntimeRole;
  ttlSec?: number;
}): Promise<GeneratorSlotLease> {
  const ttl = params.ttlSec ?? DEFAULT_LEASE_TTL_SEC;

  return db.transaction(async (tx) => {
    const now = new Date();
    const expiresAt = new Date(now.getTime() + ttl * 1000);

    const [existing] = await tx
      .select()
      .from(snowflakeGeneratorSlots)
      .where(eq(snowflakeGeneratorSlots.generatorId, params.generatorId))
      .for("update");

    if (existing) {
      const stillValid = existing.leaseExpiresAt > now;
      const nextEpoch = stillValid ? existing.leaseEpoch : existing.leaseEpoch + 1n;
      const fencing = stillValid ? existing.fencingToken : await nextFencingToken(tx as unknown as Parameters<typeof nextFencingToken>[0]);
      const [updated] = await tx
        .update(snowflakeGeneratorSlots)
        .set({
          leaseEpoch: nextEpoch,
          fencingToken: fencing,
          leaseExpiresAt: expiresAt,
          lastHeartbeatAt: now,
        })
        .where(eq(snowflakeGeneratorSlots.generatorId, params.generatorId))
        .returning();
      return toLease(updated);
    }

    // Tìm slot trống: slot có row nhưng lease hết hạn cũng coi là "chiếm được" nếu
    // ta reclaim (UPDATE row đó). Ưu tiên slot hoàn toàn chưa dùng.
    const activeRows = await tx
      .select({ slot: snowflakeGeneratorSlots.slot })
      .from(snowflakeGeneratorSlots)
      .where(gt(snowflakeGeneratorSlots.leaseExpiresAt, now));
    const activeSlots = new Set(activeRows.map((r) => r.slot));

    for (let slot = 0; slot <= MAX_SLOT; slot++) {
      if (activeSlots.has(slot)) continue;
      const fencing = await nextFencingToken(tx as unknown as Parameters<typeof nextFencingToken>[0]);
      try {
        // Reclaim row cũ của slot này (lease hết hạn) nếu có, else INSERT mới.
        const [expiredHolder] = await tx
          .select({ generatorId: snowflakeGeneratorSlots.generatorId })
          .from(snowflakeGeneratorSlots)
          .where(
            and(eq(snowflakeGeneratorSlots.slot, slot), lte(snowflakeGeneratorSlots.leaseExpiresAt, now))
          )
          .for("update");

        if (expiredHolder) {
          const [reclaimed] = await tx
            .update(snowflakeGeneratorSlots)
            .set({
              generatorId: params.generatorId,
              runtimeRole: params.runtimeRole,
              leaseEpoch: 1n,
              fencingToken: fencing,
              leaseExpiresAt: expiresAt,
              lastHeartbeatAt: now,
              clockCheckpoint: 0n,
            })
            .where(eq(snowflakeGeneratorSlots.generatorId, expiredHolder.generatorId))
            .returning();
          return toLease(reclaimed);
        }

        const [inserted] = await tx
          .insert(snowflakeGeneratorSlots)
          .values({
            generatorId: params.generatorId,
            slot,
            runtimeRole: params.runtimeRole,
            leaseEpoch: 1n,
            fencingToken: fencing,
            leaseExpiresAt: expiresAt,
            lastHeartbeatAt: now,
          })
          .returning();
        return toLease(inserted);
      } catch (err) {
        if (isUniqueViolation(err)) continue; // race — thử slot kế
        throw err;
      }
    }

    throw APIError.failedPrecondition("Hết slot Snowflake generator (1024 slot đều đang active)");
  });
}

/**
 * Heartbeat. Từ chối nếu fencing token cũ (đã bị process khác reclaim) hoặc lease
 * đã hết hạn ⇒ generator phải acquire lại. Cập nhật `clock_checkpoint` = max ms
 * timestamp đã phát ra để chống clock regression.
 */
export async function renewGeneratorLease(params: {
  generatorId: string;
  fencingToken: bigint;
  clockCheckpointMs?: bigint;
  ttlSec?: number;
}): Promise<{ leaseExpiresAt: Date }> {
  const ttl = params.ttlSec ?? DEFAULT_LEASE_TTL_SEC;
  const now = new Date();
  const expiresAt = new Date(now.getTime() + ttl * 1000);

  const rows = await db
    .update(snowflakeGeneratorSlots)
    .set({
      leaseExpiresAt: expiresAt,
      lastHeartbeatAt: now,
      ...(params.clockCheckpointMs !== undefined
        ? {
            clockCheckpoint: sql`GREATEST(${snowflakeGeneratorSlots.clockCheckpoint}, ${params.clockCheckpointMs})`,
          }
        : {}),
    })
    .where(
      and(
        eq(snowflakeGeneratorSlots.generatorId, params.generatorId),
        eq(snowflakeGeneratorSlots.fencingToken, params.fencingToken),
        gt(snowflakeGeneratorSlots.leaseExpiresAt, now)
      )
    )
    .returning({ leaseExpiresAt: snowflakeGeneratorSlots.leaseExpiresAt });

  if (rows.length === 0) {
    throw APIError.failedPrecondition(
      "Lease Snowflake không còn hợp lệ (fencing token cũ hoặc hết hạn) — cần acquire lại"
    );
  }
  return { leaseExpiresAt: rows[0].leaseExpiresAt };
}

// --- Bootstrap / heartbeat cho control-plane process ------------------------

let boundGeneratorId: string | null = null;
let boundFencingToken: bigint | null = null;

export function localGeneratorId(): string {
  return process.env.COSA_GENERATOR_ID?.trim() || `cosa:${hostname()}:${process.pid}`;
}

/**
 * Gọi lúc control-plane khởi động: acquire slot rồi cấu hình snowflake.service.
 * Registry unreachable / hết slot ⇒ ném lỗi (caller quyết định fail-closed).
 */
export async function bootstrapGeneratorSlot(): Promise<GeneratorSlotLease> {
  const generatorId = localGeneratorId();
  const lease = await acquireGeneratorSlot({
    generatorId,
    runtimeRole: "cosa_control_plane",
  });
  configureGeneratorSlot(lease.slot);
  boundGeneratorId = generatorId;
  boundFencingToken = lease.fencingToken;
  return lease;
}

/** Gia hạn lease của process hiện tại (gọi định kỳ < TTL). No-op nếu chưa bootstrap. */
export async function heartbeatBoundGenerator(clockCheckpointMs?: bigint): Promise<void> {
  if (!boundGeneratorId || boundFencingToken === null) return;
  await renewGeneratorLease({
    generatorId: boundGeneratorId,
    fencingToken: boundFencingToken,
    clockCheckpointMs,
  });
}

export async function releaseGeneratorSlot(generatorId: string): Promise<void> {
  await db
    .update(snowflakeGeneratorSlots)
    .set({ leaseExpiresAt: new Date(0) })
    .where(eq(snowflakeGeneratorSlots.generatorId, generatorId));
}

function toLease(row: typeof snowflakeGeneratorSlots.$inferSelect): GeneratorSlotLease {
  return {
    generatorId: row.generatorId,
    slot: row.slot,
    runtimeRole: row.runtimeRole as GeneratorRuntimeRole,
    leaseEpoch: row.leaseEpoch,
    fencingToken: row.fencingToken,
    leaseExpiresAt: row.leaseExpiresAt,
    clockCheckpoint: row.clockCheckpoint,
  };
}
