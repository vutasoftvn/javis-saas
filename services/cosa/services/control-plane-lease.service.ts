import { randomUUID } from "node:crypto";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";

const { runtimeLeases, workers } = schema;

/**
 * Port của packages/agent_core/runs/leases.py::RunLeaseManager sang durable
 * Postgres (ADR-CONTROLPLANE-001 §2). Bản gốc Python hoàn toàn in-memory (dict
 * + asyncio.Lock trong 1 process) — không chống split-brain thật giữa nhiều
 * process/replica. Dùng `SELECT ... FOR UPDATE` trong transaction để khoá đúng
 * row `run_id` khi acquire, tránh race giữa 2 request cùng lúc claim 1 run_id.
 *
 * ĐÃ ĐƯỢC VERIFY bằng PostgreSQL thật và multi-OS process thật qua CI gate
 * `durability` (tests/apps/cosa/worker/test_lease_mutual_exclusion_real.py và
 * tests/apps/cosa/worker/test_crash_recovery_subprocess.py — 2026-08-28 TPR Part 1C).
 */

export interface AcquireLeaseParams {
  runId: string;
  workerId: string;
  ttlSec?: number;
}

export interface LeaseResult {
  success: boolean;
  leaseToken?: string;
  expiresAt?: Date;
  reason: string;
}

const DEFAULT_TTL_SEC = 60;

export async function acquireLease(params: AcquireLeaseParams): Promise<LeaseResult> {
  const ttl = params.ttlSec ?? DEFAULT_TTL_SEC;
  const now = new Date();
  const expiresAt = new Date(now.getTime() + ttl * 1000);
  const leaseToken = `lease_${randomUUID().replace(/-/g, "").slice(0, 12)}`;

  return db.transaction(async (tx) => {
    await tx
      .insert(workers)
      .values({
        id: params.workerId,
        runtimeKind: "openai_agents",
      })
      .onConflictDoNothing();

    const existingRows = await tx
      .select()
      .from(runtimeLeases)
      .where(eq(runtimeLeases.runId, params.runId))
      .for("update");
    const existing = existingRows[0];

    if (existing && existing.expiresAt > now && existing.workerId !== params.workerId) {
      return {
        success: false,
        reason: `Run '${params.runId}' is currently leased by worker '${existing.workerId}' until ${existing.expiresAt.toISOString()}`,
      };
    }

    if (existing) {
      await tx
        .update(runtimeLeases)
        .set({ workerId: params.workerId, leaseToken, acquiredAt: now, expiresAt, heartbeatIntervalSec: ttl })
        .where(eq(runtimeLeases.runId, params.runId));
      return { success: true, leaseToken, expiresAt, reason: "Lease successfully acquired" };
    } else {
      const inserted = await tx
        .insert(runtimeLeases)
        .values({
          runId: params.runId,
          workerId: params.workerId,
          leaseToken,
          acquiredAt: now,
          expiresAt,
          heartbeatIntervalSec: ttl,
        })
        .onConflictDoNothing({ target: runtimeLeases.runId })
        .returning();

      if (inserted.length === 0) {
        // Concurrent race: another worker inserted this lease row simultaneously
        const recheckRows = await tx
          .select()
          .from(runtimeLeases)
          .where(eq(runtimeLeases.runId, params.runId))
          .for("update");
        const recheck = recheckRows[0];

        if (recheck && recheck.expiresAt > now && recheck.workerId !== params.workerId) {
          return {
            success: false,
            reason: `Run '${params.runId}' is currently leased by worker '${recheck.workerId}' until ${recheck.expiresAt.toISOString()}`,
          };
        }

        if (recheck && (recheck.expiresAt <= now || recheck.workerId === params.workerId)) {
          await tx
            .update(runtimeLeases)
            .set({ workerId: params.workerId, leaseToken, acquiredAt: now, expiresAt, heartbeatIntervalSec: ttl })
            .where(eq(runtimeLeases.runId, params.runId));
          return { success: true, leaseToken, expiresAt, reason: "Lease successfully acquired" };
        }

        return {
          success: false,
          reason: `Run '${params.runId}' could not be acquired due to concurrent lease conflict`,
        };
      }

      return { success: true, leaseToken, expiresAt, reason: "Lease successfully acquired" };
    }
  });
}

export interface RenewLeaseParams {
  runId: string;
  workerId: string;
  leaseToken: string;
  additionalTtlSec?: number;
}

export async function renewLease(params: RenewLeaseParams): Promise<boolean> {
  const ttl = params.additionalTtlSec ?? DEFAULT_TTL_SEC;
  const now = new Date();
  const expiresAt = new Date(now.getTime() + ttl * 1000);

  return db.transaction(async (tx) => {
    const existingRows = await tx
      .select()
      .from(runtimeLeases)
      .where(eq(runtimeLeases.runId, params.runId))
      .for("update");
    const existing = existingRows[0];

    if (!existing || existing.workerId !== params.workerId || existing.leaseToken !== params.leaseToken) {
      return false;
    }

    await tx.update(runtimeLeases).set({ expiresAt }).where(eq(runtimeLeases.runId, params.runId));
    return true;
  });
}

export interface ReleaseLeaseParams {
  runId: string;
  workerId: string;
  leaseToken: string;
}

export async function releaseLease(params: ReleaseLeaseParams): Promise<boolean> {
  return db.transaction(async (tx) => {
    const existingRows = await tx
      .select()
      .from(runtimeLeases)
      .where(eq(runtimeLeases.runId, params.runId))
      .for("update");
    const existing = existingRows[0];

    if (!existing || existing.workerId !== params.workerId || existing.leaseToken !== params.leaseToken) {
      return false;
    }

    await tx.delete(runtimeLeases).where(eq(runtimeLeases.runId, params.runId));
    return true;
  });
}
