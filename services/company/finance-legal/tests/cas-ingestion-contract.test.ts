// F3 — hợp đồng ingestion hợp nhất GET-poll + webhook Cas.so: normalizer
// reject đúng loại (không default 0/IN/now), dedup hội tụ về 1 canonical
// row bất kể nguồn, retry/backoff/DLQ thật qua DB (không mock chính cái đang
// test), 2 worker claim không double ingest, stale callback không đổi
// tenant, sync 401/403 -> reauth, 429/5xx -> bounded retry, first-connect
// backfill + incremental overlap window.
import { describe, expect, it } from "vitest";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  computeCasEventIdentity,
  normalizeCasTransaction,
  type NormalizerConnectionContext,
} from "../services/cas-normalizer";
import { CAS_CONTRACT } from "../services/cas-contract";
import {
  claimDueCasInboxEvents,
  completeCasInboxEvent,
  enqueueCasInboxEvent,
  failCasInboxEvent,
  INBOX_MAX_ATTEMPTS,
} from "../services/ingestion.service";
import { processCasInboxBatch } from "../services/cas-inbox-worker.service";
import { receiveCasWebhookService } from "../services/cas-webhook.service";
import { syncCasConnection, type SyncCasConnectionDeps } from "../services/cas-sync.service";
import type { CasTransactionPage } from "../services/cas-client";

const { bankConnections, bankTransactions, casSyncInbox } = schema;

async function insertConnection(p: {
  workspaceId: bigint;
  externalAccountId: string;
  consentState?: "PENDING" | "GRANTED" | "REVOKED" | "EXPIRED";
  reauthRequired?: boolean;
}) {
  const id = generateSnowflake();
  await db.insert(bankConnections).values({
    id,
    workspaceId: p.workspaceId,
    provider: "cas",
    providerEnvironment: "sandbox",
    consentState: p.consentState ?? "GRANTED",
    externalAccountId: p.externalAccountId,
    reauthRequired: p.reauthRequired ?? false,
  });
  const [row] = await db.select().from(bankConnections).where(eq(bankConnections.id, id));
  return row;
}

const ctx = (connId: bigint, wsId: bigint): NormalizerConnectionContext => ({
  id: String(connId),
  workspaceId: String(wsId),
  providerEnvironment: "sandbox",
});

describe("cas-normalizer: reject typed, không default 0/IN/now", () => {
  it("accepts a valid raw transaction", () => {
    const wsId = generateSnowflake();
    const connId = generateSnowflake();
    const result = normalizeCasTransaction(
      { tid: "tid_ok_1", amount: 250000, when: "2026-08-29T10:00:00Z", description: "test", bank_sub_acc_id: "acc_1" },
      CAS_CONTRACT,
      ctx(connId, wsId)
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.transaction.direction).toBe("IN");
      expect(result.transaction.amountMinor).toBe("250000");
      expect(result.transaction.externalTransactionId).toBe("tid_ok_1");
    }
  });

  it("rejects missing amount as INVALID_PROVIDER_PAYLOAD, not amount=0", () => {
    const result = normalizeCasTransaction(
      { tid: "tid_no_amount", when: "2026-08-29T10:00:00Z" },
      CAS_CONTRACT,
      ctx(1n, 1n)
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("INVALID_PROVIDER_PAYLOAD");
  });

  it("rejects amount=0 with no explicit direction (ambiguous), not defaulted to IN", () => {
    const result = normalizeCasTransaction(
      { tid: "tid_zero", amount: 0, when: "2026-08-29T10:00:00Z" },
      CAS_CONTRACT,
      ctx(1n, 1n)
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("INVALID_PROVIDER_PAYLOAD");
  });

  it("preserves exact amountMinor for a string amount beyond Number.MAX_SAFE_INTEGER (IA13)", () => {
    // 9007199254740993 = MAX_SAFE_INTEGER (9007199254740991) + 2 — không thể
    // biểu diễn chính xác bằng JS number (float64). Provider gửi amount dạng
    // string chính là để tránh mất chính xác này; code KHÔNG được tự ý đi
    // qua Number() rồi mất nó trước khi tới BigInt-based Money parser.
    const wsId = generateSnowflake();
    const connId = generateSnowflake();
    const result = normalizeCasTransaction(
      {
        tid: "tid_precision_1",
        amount: "9007199254740993",
        when: "2026-08-29T10:00:00Z",
        bank_sub_acc_id: "acc_1",
      },
      CAS_CONTRACT,
      ctx(connId, wsId)
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.transaction.amountMinor).toBe("9007199254740993");
      expect(result.transaction.direction).toBe("IN");
    }
  });

  it("preserves exact amountMinor for a large negative string amount (IA13)", () => {
    const wsId = generateSnowflake();
    const connId = generateSnowflake();
    const result = normalizeCasTransaction(
      {
        tid: "tid_precision_2",
        amount: "-9007199254740993",
        when: "2026-08-29T10:00:00Z",
        bank_sub_acc_id: "acc_1",
      },
      CAS_CONTRACT,
      ctx(connId, wsId)
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.transaction.amountMinor).toBe("9007199254740993");
      expect(result.transaction.direction).toBe("OUT");
    }
  });

  it("rejects missing booked time as INVALID_PROVIDER_PAYLOAD, not defaulted to now()", () => {
    const result = normalizeCasTransaction({ tid: "tid_no_time", amount: 1000 }, CAS_CONTRACT, ctx(1n, 1n));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("INVALID_PROVIDER_PAYLOAD");
  });

  it("rejects a webhook envelope with error != 0 / data null as NOT_A_TRANSACTION_EVENT-equivalent (handled upstream, not by normalizer directly)", () => {
    // normalizer chỉ nhận raw transaction record (đã unwrap khỏi envelope),
    // nên input malformed (không phải object hợp lệ) -> MALFORMED_RAW_PAYLOAD.
    const result = normalizeCasTransaction(null, CAS_CONTRACT, ctx(1n, 1n));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("MALFORMED_RAW_PAYLOAD");
  });

  it("computeCasEventIdentity is stable for same inputs regardless of extraneous raw bytes", () => {
    const a = computeCasEventIdentity({
      bankConnectionId: "conn_1",
      bankSubAccId: "acc_1",
      externalTransactionId: "tid_1",
      eventKind: "transaction",
      contractVersion: "2023-01-01",
    });
    const b = computeCasEventIdentity({
      bankConnectionId: "conn_1",
      bankSubAccId: "acc_1",
      externalTransactionId: "tid_1",
      eventKind: "transaction",
      contractVersion: "2023-01-01",
    });
    expect(a).toBe(b);
  });
});

describe("GET-poll + webhook of the same transaction converge to one canonical row", () => {
  it("dedups at inbox level (same event_identity) and produces exactly 1 bank_transaction", async () => {
    const wsId = generateSnowflake();
    const subAccId = `sub_acc_dedup_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const conn = await insertConnection({ workspaceId: wsId, externalAccountId: subAccId });

    const rawTxn = {
      id: 555001,
      tid: "cas_tid_dedup_1",
      description: "Chuyen khoan doi tac",
      amount: 3200000,
      bank_sub_acc_id: subAccId,
      when: "2026-08-29T09:30:00Z",
    };

    // Nguồn 1: GET-poll enqueue trực tiếp (giả lập cas-sync.service đã fetch xong).
    const identity = computeCasEventIdentity({
      bankConnectionId: String(conn.id),
      bankSubAccId: rawTxn.bank_sub_acc_id,
      externalTransactionId: rawTxn.tid,
      eventKind: "transaction",
      contractVersion: CAS_CONTRACT.contractVersion,
    });
    const pollEnqueue = await enqueueCasInboxEvent({
      bankConnectionId: conn.id,
      provider: "cas",
      environment: "sandbox",
      source: "poll",
      eventIdentity: identity,
      rawPayload: rawTxn,
    });
    expect(pollEnqueue.isDuplicate).toBe(false);

    // Nguồn 2: webhook giao ĐÚNG giao dịch đó — raw JSON thật (envelope
    // {id, error, data}), KHÔNG bọc trong field rawPayload string kiểu cũ.
    const webhookPayload = JSON.stringify({ id: "evt_dedup_1", error: 0, data: rawTxn });
    const webhookResult = await receiveCasWebhookService({ rawPayload: webhookPayload, skipSigVerify: true });

    // Cùng identity -> cùng 1 dòng inbox (webhook resolve đúng connection qua
    // bank_sub_acc_id nên tính ra identity giống hệt).
    expect(webhookResult.inboxId).toBe(pollEnqueue.id);
    expect(webhookResult.isDuplicate).toBe(true);
    expect(webhookResult.quarantined).toBe(false);

    const batch = await processCasInboxBatch({ limit: 10, bankConnectionId: conn.id });
    expect(batch.processed).toBe(1);

    const txns = await db
      .select()
      .from(bankTransactions)
      .where(and(eq(bankTransactions.bankConnectionId, conn.id), eq(bankTransactions.externalTransactionId, "cas_tid_dedup_1")));
    expect(txns.length).toBe(1);
    expect(Number(txns[0].amount)).toBe(3200000);
  });
});

describe("webhook: resolve tenant server-side, quarantine unknown grant, stale callback không đổi tenant", () => {
  it("resolves the correct connection from bank_sub_acc_id, not from any self-declared field", async () => {
    const wsId = generateSnowflake();
    const subAccId = `sub_acc_resolve_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    const conn = await insertConnection({ workspaceId: wsId, externalAccountId: subAccId });

    const payload = JSON.stringify({
      id: "evt_resolve_1",
      error: 0,
      data: { tid: "tid_resolve_1", amount: 10000, when: "2026-08-29T08:00:00Z", bank_sub_acc_id: subAccId },
    });
    const res = await receiveCasWebhookService({ rawPayload: payload, skipSigVerify: true });
    expect(res.quarantined).toBe(false);

    const [row] = await db.select().from(casSyncInbox).where(eq(casSyncInbox.id, BigInt(res.inboxId)));
    expect(String(row.bankConnectionId)).toBe(String(conn.id));
    // ACK ngay, KHÔNG xử lý inline — dòng vẫn RECEIVED chờ worker.
    expect(row.status).toBe("RECEIVED");
  });

  it("quarantines a webhook for an unknown bank_sub_acc_id instead of failing loudly or guessing a tenant", async () => {
    const payload = JSON.stringify({
      id: "evt_unknown_1",
      error: 0,
      data: { tid: "tid_unknown_1", amount: 5000, when: "2026-08-29T08:00:00Z", bank_sub_acc_id: "sub_acc_never_registered" },
    });
    const res = await receiveCasWebhookService({ rawPayload: payload, skipSigVerify: true });
    expect(res.quarantined).toBe(true);

    const [row] = await db.select().from(casSyncInbox).where(eq(casSyncInbox.id, BigInt(res.inboxId)));
    expect(row.bankConnectionId).toBeNull();
    expect(row.status).toBe("QUARANTINED");
  });

  it("does not attribute a late callback to a connection that was already revoked (stale callback không đổi tenant)", async () => {
    const wsId = generateSnowflake();
    const conn = await insertConnection({
      workspaceId: wsId,
      externalAccountId: "sub_acc_revoked_1",
      consentState: "REVOKED",
    });

    const payload = JSON.stringify({
      id: "evt_stale_1",
      error: 0,
      data: { tid: "tid_stale_1", amount: 7000, when: "2026-08-29T08:00:00Z", bank_sub_acc_id: "sub_acc_revoked_1" },
    });
    const res = await receiveCasWebhookService({ rawPayload: payload, skipSigVerify: true });

    expect(res.quarantined).toBe(true);
    const [row] = await db.select().from(casSyncInbox).where(eq(casSyncInbox.id, BigInt(res.inboxId)));
    expect(row.bankConnectionId).toBeNull();
    expect(String(row.bankConnectionId)).not.toBe(String(conn.id));
  });

  it("ignores non-transaction webhook events (error != 0 / data null) without treating them as invalid transactions", async () => {
    const payload = JSON.stringify({ id: "evt_grant_revoked_1", error: 1, data: null });
    const res = await receiveCasWebhookService({ rawPayload: payload, skipSigVerify: true });
    expect(res.quarantined).toBe(false);
    const [row] = await db.select().from(casSyncInbox).where(eq(casSyncInbox.id, BigInt(res.inboxId)));
    expect(row.status).toBe("IGNORED");
  });
});

describe("durable inbox: crash-then-resume, retry of FAILED, DLQ, two workers no double ingest", () => {
  it("survives a durable-commit-then-crash: a row enqueued but never processed is fully recoverable on the next (fresh) worker call", async () => {
    const wsId = generateSnowflake();
    const conn = await insertConnection({ workspaceId: wsId, externalAccountId: "sub_acc_crash_1" });
    const rawTxn = {
      tid: "tid_crash_1",
      amount: 90000,
      when: "2026-08-29T07:00:00Z",
      bank_sub_acc_id: "sub_acc_crash_1",
    };
    const identity = computeCasEventIdentity({
      bankConnectionId: String(conn.id),
      bankSubAccId: rawTxn.bank_sub_acc_id,
      externalTransactionId: rawTxn.tid,
      eventKind: "transaction",
      contractVersion: CAS_CONTRACT.contractVersion,
    });
    const enq = await enqueueCasInboxEvent({
      bankConnectionId: conn.id,
      provider: "cas",
      environment: "sandbox",
      source: "poll",
      eventIdentity: identity,
      rawPayload: rawTxn,
    });

    // "Crash" mô phỏng: KHÔNG có state nào giữ trong biến JS nào khác ngoài
    // DB — dòng inbox đã COMMIT (đọc lại độc lập từ enqueue để chứng minh nó
    // thật sự nằm trong DB, không phải object đang giữ trong tay).
    const [committedRow] = await db.select().from(casSyncInbox).where(eq(casSyncInbox.id, BigInt(enq.id)));
    expect(committedRow.status).toBe("RECEIVED");

    // "Restart": processCasInboxBatch không có state nội bộ nào từ lần gọi
    // enqueue — chỉ đọc DB. Gọi nó y như một tiến trình worker mới khởi động
    // sẽ làm, không tái dùng bất kỳ tham chiếu JS nào từ nhánh enqueue.
    const result = await processCasInboxBatch({ limit: 5, bankConnectionId: conn.id });
    expect(result.processed).toBe(1);

    const [txn] = await db
      .select()
      .from(bankTransactions)
      .where(and(eq(bankTransactions.bankConnectionId, conn.id), eq(bankTransactions.externalTransactionId, "tid_crash_1")));
    expect(txn).toBeDefined();
  });

  it("IA10: reclaims a row stuck in PROCESSING after its lease expires (worker died after claim, before complete/fail)", async () => {
    const wsId = generateSnowflake();
    const conn = await insertConnection({ workspaceId: wsId, externalAccountId: "sub_acc_stuck_processing" });
    const rawTxn = {
      tid: "tid_stuck_1",
      amount: 50000,
      when: "2026-08-29T07:00:00Z",
      bank_sub_acc_id: "sub_acc_stuck_processing",
    };
    const identity = computeCasEventIdentity({
      bankConnectionId: String(conn.id),
      bankSubAccId: rawTxn.bank_sub_acc_id,
      externalTransactionId: rawTxn.tid,
      eventKind: "transaction",
      contractVersion: CAS_CONTRACT.contractVersion,
    });
    await enqueueCasInboxEvent({
      bankConnectionId: conn.id,
      provider: "cas",
      environment: "sandbox",
      source: "poll",
      eventIdentity: identity,
      rawPayload: rawTxn,
    });

    // Worker A claim (RECEIVED -> PROCESSING), rồi "chết" — không gọi
    // completeCasInboxEvent/failCasInboxEvent với leaseToken của nó.
    const now = new Date();
    const [claimedByA] = await claimDueCasInboxEvents({ limit: 5, bankConnectionId: conn.id, now });
    expect(claimedByA.status).toBe("PROCESSING");

    // Trước khi lease hết hạn: 1 worker khác claim cùng lúc KHÔNG được nhận
    // lại dòng này (lease còn hiệu lực) — hành vi cũ vẫn phải giữ nguyên.
    const stillLeased = await claimDueCasInboxEvents({ limit: 5, bankConnectionId: conn.id, now });
    expect(stillLeased).toHaveLength(0);

    // Sau khi lease hết hạn (worker A coi như đã chết) — "worker B" (tiến
    // trình mới, không giữ leaseToken của A) phải reclaim được dòng này.
    const afterLeaseExpiry = new Date(now.getTime() + 3 * 60 * 1000); // > INBOX_LEASE_MS (2 phút)
    const [claimedByB] = await claimDueCasInboxEvents({ limit: 5, bankConnectionId: conn.id, now: afterLeaseExpiry });
    expect(claimedByB).toBeDefined();
    expect(claimedByB.status).toBe("PROCESSING");
    expect(claimedByB.leaseToken).not.toBe(claimedByA.leaseToken);

    // Worker A "sống lại" và cố complete bằng leaseToken cũ — fencing token
    // phải chặn, không được ghi đè kết quả của worker B.
    const staleComplete = await completeCasInboxEvent(BigInt(claimedByA.id), claimedByA.leaseToken);
    expect(staleComplete).toBe(false);

    // Worker B hoàn tất bằng leaseToken thật của nó — phải thành công.
    const realComplete = await completeCasInboxEvent(BigInt(claimedByB.id), claimedByB.leaseToken);
    expect(realComplete).toBe(true);

    const [finalRow] = await db.select().from(casSyncInbox).where(eq(casSyncInbox.id, BigInt(claimedByB.id)));
    expect(finalRow.status).toBe("PROCESSED");
  });

  it("retries a FAILED item on the next due claim instead of silently skipping it because it already has an event", async () => {
    const wsId = generateSnowflake();
    const conn = await insertConnection({ workspaceId: wsId, externalAccountId: "sub_acc_retry_1" });
    const badRaw = { tid: "tid_bad_1", bank_sub_acc_id: "sub_acc_retry_1" }; // thiếu amount/when

    const enq = await enqueueCasInboxEvent({
      bankConnectionId: conn.id,
      provider: "cas",
      environment: "sandbox",
      source: "poll",
      eventIdentity: `retry-test:${enqDedupSuffix()}`,
      rawPayload: badRaw,
    });

    const first = await processCasInboxBatch({ limit: 5, bankConnectionId: conn.id });
    expect(first.failed).toBe(1);

    const [afterFirst] = await db.select().from(casSyncInbox).where(eq(casSyncInbox.id, BigInt(enq.id)));
    expect(afterFirst.status).toBe("FAILED");
    expect(afterFirst.attempts).toBe(1);

    // Đẩy next_attempt_at về quá khứ để mô phỏng backoff đã hết hạn — vẫn là
    // dữ liệu thật trong DB, không mock claimDueCasInboxEvents.
    await db.update(casSyncInbox).set({ nextAttemptAt: new Date(Date.now() - 1000) }).where(eq(casSyncInbox.id, BigInt(enq.id)));

    const second = await processCasInboxBatch({ limit: 5, bankConnectionId: conn.id });
    expect(second.failed).toBe(1); // vẫn retry thật (không chỉ skip), vẫn lỗi vì payload vẫn thiếu field

    const [afterSecond] = await db.select().from(casSyncInbox).where(eq(casSyncInbox.id, BigInt(enq.id)));
    expect(afterSecond.attempts).toBe(2);
  });

  it("moves a persistently-invalid item to DLQ after INBOX_MAX_ATTEMPTS instead of retrying forever", async () => {
    const wsId = generateSnowflake();
    const conn = await insertConnection({ workspaceId: wsId, externalAccountId: "sub_acc_dlq_1" });
    const badRaw = { tid: "tid_dlq_1" }; // thiếu amount/when vĩnh viễn

    const enq = await enqueueCasInboxEvent({
      bankConnectionId: conn.id,
      provider: "cas",
      environment: "sandbox",
      source: "poll",
      eventIdentity: `dlq-test:${enqDedupSuffix()}`,
      rawPayload: badRaw,
    });

    for (let i = 0; i < INBOX_MAX_ATTEMPTS; i++) {
      await processCasInboxBatch({ limit: 5, bankConnectionId: conn.id });
      await db.update(casSyncInbox).set({ nextAttemptAt: new Date(Date.now() - 1000) }).where(eq(casSyncInbox.id, BigInt(enq.id)));
    }
    // 1 lần claim cuối để chuyển DLQ tại đúng ngưỡng.
    await processCasInboxBatch({ limit: 5, bankConnectionId: conn.id });

    const [finalRow] = await db.select().from(casSyncInbox).where(eq(casSyncInbox.id, BigInt(enq.id)));
    expect(finalRow.status).toBe("DLQ");

    const dlqRows = await db.select().from(schema.ingestionDlq).where(eq(schema.ingestionDlq.inboxEventId, BigInt(enq.id)));
    expect(dlqRows.length).toBe(1);
  });

  it("two concurrent claims never pick the same due row (no double ingest)", async () => {
    const wsId = generateSnowflake();
    const conn = await insertConnection({ workspaceId: wsId, externalAccountId: "sub_acc_concurrent_1" });
    await enqueueCasInboxEvent({
      bankConnectionId: conn.id,
      provider: "cas",
      environment: "sandbox",
      source: "poll",
      eventIdentity: `concurrent-test:${enqDedupSuffix()}`,
      rawPayload: { tid: "tid_concurrent_1", amount: 1000, when: "2026-08-29T06:00:00Z" },
    });

    const [claimA, claimB] = await Promise.all([
      claimDueCasInboxEvents({ limit: 5, bankConnectionId: conn.id }),
      claimDueCasInboxEvents({ limit: 5, bankConnectionId: conn.id }),
    ]);

    const totalClaimed = claimA.length + claimB.length;
    expect(totalClaimed).toBe(1); // FOR UPDATE SKIP LOCKED — chỉ 1 trong 2 worker thắng
  });
});

describe("syncCasConnection: first-connect backfill, incremental overlap, provider error mapping", () => {
  function fakeDeps(pages: CasTransactionPage[]): SyncCasConnectionDeps & { calls: any[] } {
    const calls: any[] = [];
    let i = 0;
    return {
      calls,
      getTransactions: async (connection, opts) => {
        calls.push({ connection, opts });
        const page = pages[Math.min(i, pages.length - 1)];
        i++;
        return page;
      },
    };
  }

  it("first connect: paginates via cursor and sets coverageStart once fully caught up", async () => {
    const wsId = generateSnowflake();
    const conn = await insertConnection({ workspaceId: wsId, externalAccountId: "sub_acc_backfill_1" });

    const deps = fakeDeps([
      {
        transactions: [
          { tid: "tid_bf_1", amount: 1000, when: "2026-08-01T00:00:00Z", bank_sub_acc_id: "sub_acc_backfill_1" } as any,
        ],
        nextCursor: "c1",
        hasMore: true,
      },
      {
        transactions: [
          { tid: "tid_bf_2", amount: 2000, when: "2026-08-02T00:00:00Z", bank_sub_acc_id: "sub_acc_backfill_1" } as any,
        ],
        nextCursor: null,
        hasMore: false,
      },
    ]);

    const result = await syncCasConnection(conn.id, conn.updatedAt.toISOString(), deps);
    expect(result.status).toBe("SYNCED");
    expect(result.pagesFetched).toBe(2);
    expect(result.coverageStart).toBeTruthy();
    expect(deps.calls[0].opts.cursor).toBeUndefined();
    expect(deps.calls[1].opts.cursor).toBe("c1");

    const txns = await db.select().from(bankTransactions).where(eq(bankTransactions.bankConnectionId, conn.id));
    expect(txns.length).toBe(2);

    const [updatedConn] = await db.select().from(bankConnections).where(eq(bankConnections.id, conn.id));
    expect(updatedConn.syncCursor).toBeNull();
    expect(updatedConn.syncCoverageStart).not.toBeNull();
  });

  it("incremental sync applies an overlap window based on lastSyncedAt to catch late transactions", async () => {
    const wsId = generateSnowflake();
    const conn = await insertConnection({ workspaceId: wsId, externalAccountId: "sub_acc_overlap_1" });

    const lastSynced = new Date("2026-08-20T00:00:00Z");
    await db
      .update(bankConnections)
      .set({ syncCursor: "existing_cursor", lastSyncedAt: lastSynced })
      .where(eq(bankConnections.id, conn.id));
    const [conn2] = await db.select().from(bankConnections).where(eq(bankConnections.id, conn.id));

    const deps = fakeDeps([{ transactions: [], nextCursor: null, hasMore: false }]);
    await syncCasConnection(conn.id, conn2.updatedAt.toISOString(), deps);

    expect(deps.calls[0].opts.cursor).toBe("existing_cursor");
    expect(deps.calls[0].opts.fromDate).toBeTruthy();
    const fromDate = new Date(deps.calls[0].opts.fromDate);
    expect(fromDate.getTime()).toBeLessThan(lastSynced.getTime());
  });

  it("maps a 401/403-equivalent provider error to REAUTH_REQUIRED and flags the connection", async () => {
    const wsId = generateSnowflake();
    const conn = await insertConnection({ workspaceId: wsId, externalAccountId: "sub_acc_reauth_1" });

    const deps: SyncCasConnectionDeps = {
      getTransactions: async () => {
        throw new Error("CAS_GRANT_REVOKED: Cas.so returned 401");
      },
    };
    const result = await syncCasConnection(conn.id, conn.updatedAt.toISOString(), deps);
    expect(result.status).toBe("REAUTH_REQUIRED");

    const [updatedConn] = await db.select().from(bankConnections).where(eq(bankConnections.id, conn.id));
    expect(updatedConn.reauthRequired).toBe(true);
  });

  it("maps a 429-equivalent provider error to RATE_LIMITED (bounded retry via next tick), not a hard failure", async () => {
    const wsId = generateSnowflake();
    const conn = await insertConnection({ workspaceId: wsId, externalAccountId: "sub_acc_ratelimit_1" });

    const deps: SyncCasConnectionDeps = {
      getTransactions: async () => {
        throw new Error("CAS_RATE_LIMITED: Retry after 60s");
      },
    };
    const result = await syncCasConnection(conn.id, conn.updatedAt.toISOString(), deps);
    expect(result.status).toBe("RATE_LIMITED");

    const [updatedConn] = await db.select().from(bankConnections).where(eq(bankConnections.id, conn.id));
    expect(updatedConn.reauthRequired).toBe(false);
    expect(updatedConn.consentState).toBe("GRANTED");
    expect(updatedConn.syncLockedUntil).toBeNull(); // lease được nhả để lần sau (worker khác/tick khác) retry được
  });

  it("refuses to sync under a stale grant version and never calls the provider", async () => {
    const wsId = generateSnowflake();
    const conn = await insertConnection({ workspaceId: wsId, externalAccountId: "sub_acc_stale_ver_1" });

    const deps = fakeDeps([{ transactions: [], nextCursor: null, hasMore: false }]);
    const result = await syncCasConnection(conn.id, "2000-01-01T00:00:00.000Z", deps);

    expect(result.status).toBe("STALE_GRANT");
    expect(deps.calls.length).toBe(0);
  });
});

let dedupCounter = 0;
function enqDedupSuffix(): string {
  dedupCounter += 1;
  return `${Date.now()}_${dedupCounter}_${Math.random().toString(36).slice(2)}`;
}
