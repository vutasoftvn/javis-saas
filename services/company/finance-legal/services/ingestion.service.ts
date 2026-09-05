// F3 — tầng "repository" cho cas_sync_inbox: claim/complete/fail/DLQ theo
// pattern lease-based đã dùng ở services/company/events/shared/events/
// outbox.repository.ts (claim due rows với FOR UPDATE SKIP LOCKED, lease
// token để chỉ chủ claim mới được complete/fail chính dòng đó). Đây là hộp
// thư HỢP NHẤT cho cả webhook (Cas.so đẩy) và GET-poll (Cas.so kéo) — xem
// cas-webhook.service.ts và cas-sync.service.ts là 2 "producer", còn
// cas-inbox-worker.service.ts là "consumer" dùng các hàm claim/complete/fail
// ở đây.
import { APIError } from "encore.dev/api";
import { randomUUID, createHash } from "node:crypto";
import { and, eq, inArray, isNull, lte, or, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { casSyncInbox, ingestionDlq, ingestionEvents, bankConnections } = schema;

// --- pre-F3 (giữ nguyên contract, có test riêng ở finance-tt58.test.ts) ---
// `ingestion_events` không còn được pipeline hợp nhất dùng (xem
// cas_sync_inbox bên dưới) nhưng vẫn giữ nguyên hàm này — có call site test
// đã tồn tại từ trước F3, xoá đi sẽ phá test không thuộc phạm vi task này.
export interface IngestionEventView {
  id: string;
  bankConnectionId: string;
  providerEventId: string;
  receivedAt: string;
  status: "RECEIVED" | "PROCESSING" | "PROCESSED" | "FAILED" | "DLQ";
  errorMsg: string | null;
  processedAt: string | null;
}

export async function recordIngestionEventService(p: {
  bankConnectionId: bigint;
  providerEventId: string;
  rawPayloadRef?: string;
  payloadStr?: string;
}): Promise<{ event: IngestionEventView; isDuplicate: boolean }> {
  const [conn] = await db.select().from(bankConnections).where(eq(bankConnections.id, p.bankConnectionId));
  if (!conn) {
    throw APIError.notFound(`Bank connection '${p.bankConnectionId}' not found`);
  }

  const [existing] = await db
    .select()
    .from(ingestionEvents)
    .where(
      and(
        eq(ingestionEvents.bankConnectionId, p.bankConnectionId),
        eq(ingestionEvents.providerEventId, p.providerEventId)
      )
    );

  if (existing) {
    return {
      event: {
        id: String(existing.id),
        bankConnectionId: String(existing.bankConnectionId),
        providerEventId: existing.providerEventId,
        receivedAt: existing.receivedAt.toISOString(),
        status: existing.status as any,
        errorMsg: existing.errorMsg,
        processedAt: existing.processedAt ? existing.processedAt.toISOString() : null,
      },
      isDuplicate: true,
    };
  }

  const checksum = p.payloadStr ? createHash("sha256").update(p.payloadStr).digest("hex") : null;

  const newId = generateSnowflake();
  const [created] = await db
    .insert(ingestionEvents)
    .values({
      id: newId,
      bankConnectionId: p.bankConnectionId,
      providerEventId: p.providerEventId,
      rawPayloadRef: p.rawPayloadRef ?? null,
      checksum,
      status: "RECEIVED",
    })
    .returning();

  return {
    event: {
      id: String(created.id),
      bankConnectionId: String(created.bankConnectionId),
      providerEventId: created.providerEventId,
      receivedAt: created.receivedAt.toISOString(),
      status: created.status as any,
      errorMsg: null,
      processedAt: null,
    },
    isDuplicate: false,
  };
}

// --- F3: repository cho cas_sync_inbox (hộp thư hợp nhất) ---

// Lease đủ dài để 1 batch normalize + ghi bank_transactions hoàn tất bình
// thường, nhưng đủ ngắn để worker khác chiếm lại nhanh nếu process crash.
export const INBOX_LEASE_MS = 2 * 60 * 1000;
export const INBOX_MAX_ATTEMPTS = 8;
const BACKOFF_BASE_MS = 5_000;
const BACKOFF_CAP_MS = 10 * 60 * 1000;

export type CasInboxStatus =
  | "RECEIVED"
  | "PROCESSING"
  | "PROCESSED"
  | "FAILED"
  | "DLQ"
  | "QUARANTINED"
  | "IGNORED";

export interface CasInboxRow {
  id: string;
  bankConnectionId: string | null;
  provider: string;
  environment: string;
  source: string;
  eventIdentity: string;
  status: CasInboxStatus;
  attempts: number;
}

export interface ClaimedCasInboxRow extends CasInboxRow {
  rawPayload: unknown;
  leaseToken: string;
}

/**
 * Ghi 1 sự kiện thô vào inbox, dedup theo (provider, environment,
 * event_identity). Idempotent: gọi lại với cùng identity trả về dòng đã có,
 * KHÔNG tạo dòng mới, KHÔNG đổi trạng thái dòng cũ (vd. dòng đã PROCESSED thì
 * vẫn PROCESSED — duplicate không "hồi sinh" một sự kiện đã xử lý xong).
 */
export async function enqueueCasInboxEvent(p: {
  bankConnectionId: bigint | null;
  provider: string;
  environment: string;
  source: "webhook" | "poll";
  eventIdentity: string;
  rawPayload: unknown;
  initialStatus?: CasInboxStatus;
}): Promise<{ id: string; isDuplicate: boolean; status: CasInboxStatus }> {
  const newId = generateSnowflake();
  const inserted = await db
    .insert(casSyncInbox)
    .values({
      id: newId,
      bankConnectionId: p.bankConnectionId,
      provider: p.provider,
      environment: p.environment,
      source: p.source,
      eventIdentity: p.eventIdentity,
      rawPayload: p.rawPayload as any,
      status: p.initialStatus ?? "RECEIVED",
    })
    .onConflictDoNothing({
      target: [casSyncInbox.provider, casSyncInbox.environment, casSyncInbox.eventIdentity],
    })
    .returning({ id: casSyncInbox.id, status: casSyncInbox.status });

  if (inserted.length === 1) {
    return { id: String(inserted[0].id), isDuplicate: false, status: inserted[0].status as CasInboxStatus };
  }

  const [existing] = await db
    .select({ id: casSyncInbox.id, status: casSyncInbox.status })
    .from(casSyncInbox)
    .where(
      and(
        eq(casSyncInbox.provider, p.provider),
        eq(casSyncInbox.environment, p.environment),
        eq(casSyncInbox.eventIdentity, p.eventIdentity)
      )
    );
  return { id: String(existing.id), isDuplicate: true, status: existing.status as CasInboxStatus };
}

/**
 * Claim tối đa `limit` dòng đến hạn xử lý (RECEIVED hoặc FAILED đã hết
 * next_attempt_at) và không đang bị lease bởi worker khác. FOR UPDATE SKIP
 * LOCKED để 2 worker chạy đồng thời không claim trùng dòng (test
 * "hai worker claim không double ingest").
 */
export async function claimDueCasInboxEvents(opts: {
  limit: number;
  now?: Date;
  bankConnectionId?: bigint;
}): Promise<ClaimedCasInboxRow[]> {
  const now = opts.now ?? new Date();
  const leaseToken = `inbox:${randomUUID().slice(0, 12)}`;

  return db.transaction(async (tx) => {
    const due = await tx
      .select()
      .from(casSyncInbox)
      .where(
        and(
          inArray(casSyncInbox.status, ["RECEIVED", "FAILED"]),
          lte(casSyncInbox.nextAttemptAt, now),
          or(isNull(casSyncInbox.leaseUntil), lte(casSyncInbox.leaseUntil, now)),
          opts.bankConnectionId !== undefined
            ? eq(casSyncInbox.bankConnectionId, opts.bankConnectionId)
            : undefined
        )
      )
      .orderBy(casSyncInbox.receivedAt)
      .limit(opts.limit)
      .for("update", { skipLocked: true });

    if (due.length === 0) return [];

    const ids = due.map((r) => r.id);
    await tx
      .update(casSyncInbox)
      .set({
        status: "PROCESSING",
        leaseUntil: new Date(now.getTime() + INBOX_LEASE_MS),
        leaseToken,
        attempts: sql`${casSyncInbox.attempts} + 1`,
      })
      .where(inArray(casSyncInbox.id, ids));

    return due.map((r) => ({
      id: String(r.id),
      bankConnectionId: r.bankConnectionId !== null ? String(r.bankConnectionId) : null,
      provider: r.provider,
      environment: r.environment,
      source: r.source,
      eventIdentity: r.eventIdentity,
      status: "PROCESSING" as const,
      attempts: r.attempts + 1,
      rawPayload: r.rawPayload,
      leaseToken,
    }));
  });
}

/**
 * Đánh dấu 1 dòng đã xử lý xong. Chỉ áp dụng nếu leaseToken khớp — tránh
 * worker A hoàn tất nhầm dòng mà worker B đang lease (lease đã hết hạn và bị
 * worker khác claim lại).
 */
export async function completeCasInboxEvent(
  id: bigint,
  leaseToken: string,
  bankTransactionId?: bigint | null
): Promise<boolean> {
  const res = await db
    .update(casSyncInbox)
    .set({
      status: "PROCESSED",
      processedAt: new Date(),
      leaseUntil: null,
      leaseToken: null,
      bankTransactionId: bankTransactionId ?? null,
    })
    .where(and(eq(casSyncInbox.id, id), eq(casSyncInbox.leaseToken, leaseToken)))
    .returning({ id: casSyncInbox.id });
  return res.length === 1;
}

/**
 * Đánh dấu 1 dòng thất bại. Backoff exponential có cap; vượt
 * INBOX_MAX_ATTEMPTS thì chuyển DLQ thay vì retry vô hạn. Dòng FAILED vẫn
 * nằm trong tập "due" của claimDueCasInboxEvents lần sau (không bị worker bỏ
 * qua chỉ vì "đã có event" — retry thật, không chỉ skip).
 */
export async function failCasInboxEvent(p: {
  id: bigint;
  leaseToken: string;
  errorCode: string;
  errorMsg: string;
  attempts: number;
  bankConnectionId: bigint | null;
  now?: Date;
}): Promise<{ movedToDlq: boolean }> {
  const now = p.now ?? new Date();
  const isDead = p.attempts >= INBOX_MAX_ATTEMPTS;
  const backoffMs = Math.min(BACKOFF_CAP_MS, BACKOFF_BASE_MS * 2 ** Math.max(p.attempts - 1, 0));

  const res = await db
    .update(casSyncInbox)
    .set({
      status: isDead ? "DLQ" : "FAILED",
      errorCode: p.errorCode,
      errorMsg: p.errorMsg,
      leaseUntil: null,
      leaseToken: null,
      nextAttemptAt: isDead ? now : new Date(now.getTime() + backoffMs),
    })
    .where(and(eq(casSyncInbox.id, p.id), eq(casSyncInbox.leaseToken, p.leaseToken)))
    .returning({ id: casSyncInbox.id });

  if (res.length !== 1) {
    // Lease đã bị worker khác lấy lại (mất lease do timeout) — không ghi đè.
    return { movedToDlq: false };
  }

  if (isDead) {
    await db.insert(ingestionDlq).values({
      id: generateSnowflake(),
      inboxEventId: p.id,
      bankConnectionId: p.bankConnectionId,
      failCount: p.attempts,
      lastError: `${p.errorCode}: ${p.errorMsg}`,
    });
  }

  return { movedToDlq: isDead };
}
