// F3 — GET-poll: kéo lịch sử/giao dịch mới từ Cas.so, đẩy vào cùng
// cas_sync_inbox mà webhook dùng, rồi drain ngay bằng cas-inbox-worker trước
// khi advance cursor. Đây là "producer" thứ 2 của pipeline hợp nhất (producer
// thứ 1 là cas-webhook.service.ts).
import { APIError } from "encore.dev/api";
import { and, eq, inArray, isNull, lte, or, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { CAS_CONTRACT } from "./cas-contract";
import type { CasTransactionPage } from "./cas-client";
import { computeCasEventIdentity } from "./cas-normalizer";
import { enqueueCasInboxEvent } from "./ingestion.service";
import { processCasInboxBatch } from "./cas-inbox-worker.service";

const { bankConnections, casSyncInbox } = schema;

const SYNC_LEASE_MS = 5 * 60 * 1000; // 5 phút — đủ cho vài trang GET + drain
const OVERLAP_WINDOW_MS = 48 * 60 * 60 * 1000; // 48h — bù giao dịch báo trễ
const DEFAULT_MAX_PAGES = 20;
const DEFAULT_PAGE_LIMIT = 100;
// Connection coi là "đến hạn" đồng bộ định kỳ nếu lần sync thành công gần
// nhất cách đây >= khoảng này (hoặc chưa từng sync).
const DEFAULT_SYNC_INTERVAL_MS = 15 * 60 * 1000;

export interface ConnectionRef {
  id: string;
  providerEnvironment: string;
}

export interface SyncCasConnectionDeps {
  getTransactions: (
    connection: ConnectionRef,
    opts: { cursor?: string; fromDate?: string; limit?: number }
  ) => Promise<CasTransactionPage>;
  now?: Date;
  maxPages?: number;
  pageLimit?: number;
}

export type SyncCasConnectionStatus =
  | "SYNCED"
  | "PARTIAL" // 1+ trang enqueue thành công nhưng còn sót canonical write chưa commit — cursor không advance hết
  | "STALE_GRANT"
  | "NOT_GRANTED"
  | "REAUTH_REQUIRED"
  | "RATE_LIMITED"
  | "PROVIDER_ERROR";

export interface SyncCasConnectionResult {
  connectionId: string;
  status: SyncCasConnectionStatus;
  pagesFetched: number;
  transactionsEnqueued: number;
  cursor: string | null;
  coverageStart: string | null;
  errorMessage?: string;
}

/**
 * expectedGrantVersion = ISO string của bank_connections.updated_at đọc được
 * TẠI thời điểm caller quyết định sync (không phải cột grant_version riêng —
 * updatedAt đã được cas-link.service bump mỗi lần revoke/reauthorize, đủ dùng
 * làm optimistic-lock version, tránh phình schema). Nếu updatedAt đã đổi
 * (revoke/reauth xảy ra giữa lúc caller đọc và lúc job thực sự chạy) —
 * KHÔNG sync dưới giả định grant cũ, trả STALE_GRANT ngay, không claim lease.
 */
export async function syncCasConnection(
  connectionId: bigint,
  expectedGrantVersion: string,
  deps: SyncCasConnectionDeps
): Promise<SyncCasConnectionResult> {
  const now = deps.now ?? new Date();
  const maxPages = deps.maxPages ?? DEFAULT_MAX_PAGES;
  const pageLimit = deps.pageLimit ?? DEFAULT_PAGE_LIMIT;

  const [connection] = await db.select().from(bankConnections).where(eq(bankConnections.id, connectionId));
  if (!connection) {
    throw APIError.notFound(`bank_connection ${connectionId} not found`);
  }

  const baseResult = (status: SyncCasConnectionStatus, errorMessage?: string): SyncCasConnectionResult => ({
    connectionId: String(connectionId),
    status,
    pagesFetched: 0,
    transactionsEnqueued: 0,
    cursor: connection.syncCursor ?? null,
    coverageStart: connection.syncCoverageStart ? connection.syncCoverageStart.toISOString() : null,
    errorMessage,
  });

  const currentVersion = connection.updatedAt.toISOString();
  if (currentVersion !== expectedGrantVersion) {
    return baseResult(
      "STALE_GRANT",
      "grant version changed since caller read the connection — refusing to sync under a stale grant assumption"
    );
  }

  if (connection.consentState !== "GRANTED") {
    return baseResult("NOT_GRANTED", `consentState=${connection.consentState}`);
  }

  if (connection.reauthRequired) {
    return baseResult("REAUTH_REQUIRED", "connection previously flagged reauth_required");
  }

  // Claim lease cấp-connection (khác lease cấp-dòng của inbox) — chặn 2
  // worker cùng poll 1 connection song song ("hai worker claim không double
  // ingest" áp dụng ở cả 2 tầng). Điều kiện updated_at không đổi được gộp
  // vào cùng UPDATE để atomic với optimistic-lock version check ở trên —
  // so sánh sau khi date_trunc('milliseconds', ...) cả 2 phía: cột
  // updated_at ở Postgres có độ chính xác microsecond, còn JS Date (đọc lại
  // ở dòng connection.updatedAt phía trên) chỉ giữ millisecond — so sánh
  // trực tiếp eq() sẽ luôn lệch dù hiển thị ISO string giống nhau.
  const claimed = await db
    .update(bankConnections)
    .set({ syncLockedUntil: new Date(now.getTime() + SYNC_LEASE_MS), syncStatus: "SYNCING" })
    .where(
      and(
        eq(bankConnections.id, connectionId),
        sql`date_trunc('milliseconds', ${bankConnections.updatedAt}) = ${connection.updatedAt}`,
        or(isNull(bankConnections.syncLockedUntil), lte(bankConnections.syncLockedUntil, now))
      )
    )
    .returning({ id: bankConnections.id });

  if (claimed.length === 0) {
    return baseResult("STALE_GRANT", "could not claim sync lease — locked by another worker or grant changed concurrently");
  }

  const connectionRef: ConnectionRef = { id: String(connection.id), providerEnvironment: connection.providerEnvironment };
  const isFirstSync = !connection.syncCursor;
  const fromDate =
    !isFirstSync && connection.lastSyncedAt
      ? new Date(connection.lastSyncedAt.getTime() - OVERLAP_WINDOW_MS).toISOString().slice(0, 10)
      : undefined;

  let cursor: string | null = connection.syncCursor ?? null;
  let pagesFetched = 0;
  let transactionsEnqueued = 0;
  let fullyDrained = true;
  let terminalStatus: SyncCasConnectionStatus = "SYNCED";
  let errorMessage: string | undefined;
  let reachedEnd = false;

  try {
    for (let page = 0; page < maxPages; page++) {
      const result = await deps.getTransactions(connectionRef, {
        cursor: cursor ?? undefined,
        fromDate,
        limit: pageLimit,
      });
      pagesFetched++;

      const pageIdentities: string[] = [];
      for (const rawTxn of result.transactions) {
        const rec = rawTxn as unknown as Record<string, unknown>;
        const externalTransactionId =
          typeof rec.tid === "string" && rec.tid.trim() ? rec.tid : rec.id !== undefined ? String(rec.id) : null;
        if (!externalTransactionId) continue; // normalizer sẽ reject INVALID_PROVIDER_PAYLOAD nếu vẫn thiếu ở bước sau; ở đây bỏ qua item không thể định danh để không làm hỏng cả trang
        const bankSubAccId = typeof rec.bank_sub_acc_id === "string" ? rec.bank_sub_acc_id : null;
        const identity = computeCasEventIdentity({
          bankConnectionId: connectionRef.id,
          bankSubAccId,
          externalTransactionId,
          eventKind: "transaction",
          contractVersion: CAS_CONTRACT.contractVersion,
        });
        await enqueueCasInboxEvent({
          bankConnectionId: connectionId,
          provider: "cas",
          environment: connection.providerEnvironment,
          source: "poll",
          eventIdentity: identity,
          rawPayload: rawTxn,
        });
        pageIdentities.push(identity);
        transactionsEnqueued++;
      }

      if (pageIdentities.length > 0) {
        // Drain ngay các dòng vừa enqueue của TRANG này trước khi advance
        // cursor — nếu process crash ngay sau bước này (đã ACK/commit inbox
        // nhưng chưa kịp normalize), cursor CHƯA advance, lần sync sau sẽ
        // fetch lại đúng trang này và enqueue lại (idempotent, dedup theo
        // event_identity) rồi drain tiếp — tự phục hồi, không mất giao dịch.
        // KHÔNG truyền `now` (đã chốt từ đầu hàm) vào đây — dòng vừa enqueue
        // nhận next_attempt_at mặc định theo now() THẬT của Postgres tại lúc
        // insert, có thể muộn hơn vài ms so với `now` JS chốt ở đầu hàm; nếu
        // truyền `now` cũ vào, điều kiện "đến hạn" (next_attempt_at <= now)
        // sẽ sai lệch và bỏ sót đúng dòng vừa tạo. Để claim tự lấy thời điểm
        // thật tại lúc gọi (luôn >= next_attempt_at của dòng vừa insert).
        await processCasInboxBatch({ limit: pageIdentities.length, bankConnectionId: connectionId });

        const pending = await db
          .select({ id: casSyncInbox.id })
          .from(casSyncInbox)
          .where(
            and(
              inArray(casSyncInbox.eventIdentity, pageIdentities),
              inArray(casSyncInbox.status, ["RECEIVED", "PROCESSING", "FAILED"])
            )
          );

        if (pending.length > 0) {
          // Còn sót canonical write chưa commit cho trang này (lỗi tạm thời,
          // hoặc batch limit chưa đủ) — KHÔNG advance cursor qua trang này.
          fullyDrained = false;
          terminalStatus = "PARTIAL";
          break;
        }
      }

      cursor = result.nextCursor;
      if (!result.hasMore) {
        reachedEnd = true;
        break;
      }
    }
  } catch (err: any) {
    const message = err?.message ? String(err.message) : String(err);
    if (message.includes("CAS_GRANT_REVOKED")) {
      await db
        .update(bankConnections)
        .set({ syncStatus: "REAUTH_REQUIRED", reauthRequired: true, syncError: message, syncLockedUntil: null })
        .where(eq(bankConnections.id, connectionId));
      return { ...baseResult("REAUTH_REQUIRED", message), pagesFetched, transactionsEnqueued };
    }
    if (message.includes("CAS_RATE_LIMITED")) {
      terminalStatus = "RATE_LIMITED";
    } else {
      terminalStatus = "PROVIDER_ERROR";
    }
    errorMessage = message;
    fullyDrained = false;
  }

  const newCoverageStart = isFirstSync && reachedEnd ? now : connection.syncCoverageStart ?? null;

  await db
    .update(bankConnections)
    .set({
      syncCursor: cursor,
      syncCoverageStart: newCoverageStart,
      syncLockedUntil: null,
      syncStatus: fullyDrained ? "IDLE" : terminalStatus,
      syncError: errorMessage ?? null,
      syncErrorCount: errorMessage ? connection.syncErrorCount + 1 : 0,
      lastSyncedAt: fullyDrained ? now : connection.lastSyncedAt,
    })
    .where(eq(bankConnections.id, connectionId));

  return {
    connectionId: String(connectionId),
    status: fullyDrained ? "SYNCED" : terminalStatus,
    pagesFetched,
    transactionsEnqueued,
    cursor,
    coverageStart: newCoverageStart ? newCoverageStart.toISOString() : null,
    errorMessage,
  };
}

/**
 * Resolve tenant CHO WEBHOOK: map bank_sub_acc_id (account identifier trong
 * raw contract Cas.so) -> bank_connections đang GRANTED. KHÔNG tin field tự
 * khai (connectionId/workspaceId) trong payload — luôn tra map phía server.
 * Chỉ khớp connection còn GRANTED: callback trễ tới sau khi connection đã bị
 * REVOKED sẽ không resolve ra connection đó nữa ("stale callback không đổi
 * tenant").
 */
export async function resolveBankConnectionForCasAccount(p: {
  bankSubAccId: string;
  environment: string;
}): Promise<{ id: string; workspaceId: string; providerEnvironment: string } | null> {
  const [connection] = await db
    .select()
    .from(bankConnections)
    .where(
      and(
        eq(bankConnections.provider, "cas"),
        eq(bankConnections.providerEnvironment, p.environment),
        eq(bankConnections.externalAccountId, p.bankSubAccId),
        eq(bankConnections.consentState, "GRANTED")
      )
    );
  if (!connection) return null;
  return {
    id: String(connection.id),
    workspaceId: String(connection.workspaceId),
    providerEnvironment: connection.providerEnvironment,
  };
}

/**
 * Connection "đến hạn" đồng bộ định kỳ: GRANTED, không đang bị lease, và
 * (chưa từng sync HOẶC lần sync thành công gần nhất đã quá interval).
 */
export async function dueCasConnectionsForSync(now: Date = new Date(), intervalMs: number = DEFAULT_SYNC_INTERVAL_MS) {
  const rows = await db.select().from(bankConnections).where(eq(bankConnections.consentState, "GRANTED"));
  return rows.filter((c) => {
    if (c.reauthRequired) return false;
    if (c.syncLockedUntil && c.syncLockedUntil > now) return false;
    if (!c.lastSyncedAt) return true;
    return now.getTime() - c.lastSyncedAt.getTime() >= intervalMs;
  });
}

/**
 * Tick định kỳ (gọi từ cron): lặp qua các connection đến hạn, sync từng cái.
 * Lỗi ở 1 connection không chặn các connection khác trong cùng tick.
 */
export async function runCasSyncTick(
  deps: Omit<SyncCasConnectionDeps, "now"> & { now?: Date },
  intervalMs: number = DEFAULT_SYNC_INTERVAL_MS
): Promise<SyncCasConnectionResult[]> {
  const now = deps.now ?? new Date();
  const due = await dueCasConnectionsForSync(now, intervalMs);
  const results: SyncCasConnectionResult[] = [];
  for (const connection of due) {
    try {
      const result = await syncCasConnection(connection.id, connection.updatedAt.toISOString(), { ...deps, now });
      results.push(result);
    } catch (err: any) {
      results.push({
        connectionId: String(connection.id),
        status: "PROVIDER_ERROR",
        pagesFetched: 0,
        transactionsEnqueued: 0,
        cursor: connection.syncCursor ?? null,
        coverageStart: connection.syncCoverageStart ? connection.syncCoverageStart.toISOString() : null,
        errorMessage: err?.message ? String(err.message) : String(err),
      });
    }
  }
  return results;
}
