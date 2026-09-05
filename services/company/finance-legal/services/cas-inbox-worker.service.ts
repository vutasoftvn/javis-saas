// F3 — consumer duy nhất của cas_sync_inbox: claim theo lease, normalize,
// ghi canonical bank_transaction, rồi complete/fail/DLQ. Dùng CHUNG cho cả
// sự kiện nguồn 'webhook' và 'poll' — đây chính là nơi "GET + webhook vào
// cùng ingestion" hội tụ thành một pipeline duy nhất.
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { CAS_CONTRACT } from "./cas-contract";
import { computeCanonicalContentHash, normalizeCasTransaction } from "./cas-normalizer";
import {
  claimDueCasInboxEvents,
  completeCasInboxEvent,
  failCasInboxEvent,
  type ClaimedCasInboxRow,
} from "./ingestion.service";
import { formatMoneyToDecimal } from "./money";
import { ingestBankTransactionIdempotent } from "./bank-transaction.service";

const { bankConnections, casNormalizerLog } = schema;

export interface ProcessCasInboxBatchResult {
  claimed: number;
  processed: number;
  failed: number;
  dlq: number;
}

export type ProcessOneOutcome = "PROCESSED" | "FAILED" | "DLQ";

/**
 * Claim tối đa `opts.limit` dòng đến hạn và xử lý tuần tự. `bankConnectionId`
 * tuỳ chọn cho phép syncCasConnection "drain" ngay các dòng vừa poll xong của
 * riêng connection đó (để chỉ advance cursor sau khi canonical writes commit)
 * mà không đụng vào backlog của các connection khác.
 */
export async function processCasInboxBatch(opts: {
  limit: number;
  now?: Date;
  bankConnectionId?: bigint;
}): Promise<ProcessCasInboxBatchResult> {
  const now = opts.now ?? new Date();
  const rows = await claimDueCasInboxEvents({
    limit: opts.limit,
    now,
    bankConnectionId: opts.bankConnectionId,
  });

  let processed = 0;
  let failed = 0;
  let dlq = 0;

  for (const row of rows) {
    const outcome = await processOneClaimedRow(row, now);
    if (outcome === "PROCESSED") processed++;
    else if (outcome === "DLQ") dlq++;
    else failed++;
  }

  return { claimed: rows.length, processed, failed, dlq };
}

async function processOneClaimedRow(row: ClaimedCasInboxRow, now: Date): Promise<ProcessOneOutcome> {
  if (!row.bankConnectionId) {
    // Claim query đã loại QUARANTINED (bankConnectionId null gắn với status
    // QUARANTINED) — đây là lưới an toàn phòng invariant bị vi phạm, không kỳ
    // vọng nhánh này chạy trong vận hành bình thường.
    const res = await failCasInboxEvent({
      id: BigInt(row.id),
      leaseToken: row.leaseToken,
      errorCode: "NO_CONNECTION",
      errorMsg: "inbox row claimed without a resolved bank_connection_id",
      attempts: row.attempts,
      bankConnectionId: null,
      now,
    });
    return res.movedToDlq ? "DLQ" : "FAILED";
  }

  const bankConnectionId = BigInt(row.bankConnectionId);

  const [connection] = await db
    .select()
    .from(bankConnections)
    .where(eq(bankConnections.id, bankConnectionId));

  if (!connection) {
    const res = await failCasInboxEvent({
      id: BigInt(row.id),
      leaseToken: row.leaseToken,
      errorCode: "CONNECTION_NOT_FOUND",
      errorMsg: `bank_connection ${row.bankConnectionId} not found`,
      attempts: row.attempts,
      bankConnectionId,
      now,
    });
    return res.movedToDlq ? "DLQ" : "FAILED";
  }

  const result = normalizeCasTransaction(row.rawPayload, CAS_CONTRACT, {
    id: String(connection.id),
    workspaceId: String(connection.workspaceId),
    providerEnvironment: connection.providerEnvironment,
  });

  if (!result.ok) {
    // Payload không hợp lệ / không phải sự kiện giao dịch — KHÔNG ghi
    // cas_normalizer_log (bảng đó dành cho audit trail giao dịch có identity
    // ổn định, không phải nơi chứa lỗi chung). Lỗi đã có chỗ durable là
    // cas_sync_inbox.error_code/error_msg + ingestion_dlq khi vượt max retry.
    const res = await failCasInboxEvent({
      id: BigInt(row.id),
      leaseToken: row.leaseToken,
      errorCode: result.reason,
      errorMsg: result.detail,
      attempts: row.attempts,
      bankConnectionId,
      now,
    });
    return res.movedToDlq ? "DLQ" : "FAILED";
  }

  const tx = result.transaction;
  const contentHash = computeCanonicalContentHash(tx);

  const [existingLog] = await db
    .select()
    .from(casNormalizerLog)
    .where(
      and(eq(casNormalizerLog.bankConnectionId, bankConnectionId), eq(casNormalizerLog.providerTxId, tx.externalTransactionId))
    );

  if (existingLog && existingLog.providerTxHash !== contentHash) {
    // Cùng provider_tx_id nhưng nội dung khác — nghi correction/reversal.
    // KHÔNG tự overwrite bank_transaction đã ghi (có thể đã đối soát) — ghi
    // nhận CONFLICT để người review, giữ nguyên bankTransactionId cũ.
    await db
      .insert(casNormalizerLog)
      .values({
        id: generateSnowflake(),
        bankConnectionId,
        inboxEventId: BigInt(row.id),
        providerTxId: tx.externalTransactionId,
        providerTxHash: contentHash,
        bankTransactionId: existingLog.bankTransactionId,
        action: "CONFLICT",
        failReason: "provider_tx_id repeated with different canonical content — needs manual review",
      })
      .onConflictDoUpdate({
        target: [casNormalizerLog.bankConnectionId, casNormalizerLog.providerTxId],
        set: {
          inboxEventId: BigInt(row.id),
          action: "CONFLICT",
          failReason: "provider_tx_id repeated with different canonical content — needs manual review",
          normalizedAt: new Date(),
        },
      });

    const res = await failCasInboxEvent({
      id: BigInt(row.id),
      leaseToken: row.leaseToken,
      errorCode: "CONFLICTING_DUPLICATE",
      errorMsg: `provider_tx_id ${tx.externalTransactionId} content hash mismatch with previously ingested transaction`,
      attempts: row.attempts,
      bankConnectionId,
      now,
    });
    return res.movedToDlq ? "DLQ" : "FAILED";
  }

  // amount column của bank_transactions là DECIMAL theo currency (không phải
  // minor units) — chuyển amountMinor -> decimal trước khi ghi, tránh lệch
  // 100x nếu tương lai có currency với decimals > 0.
  const amountDecimal = formatMoneyToDecimal({ minor: tx.amountMinor, currency: tx.currency });

  const upsert = await ingestBankTransactionIdempotent({
    workspaceId: BigInt(tx.workspaceId),
    bankConnectionId: BigInt(tx.bankConnectionId),
    externalTransactionId: tx.externalTransactionId,
    postedAt: tx.bookedAt,
    amount: amountDecimal,
    currency: tx.currency,
    direction: tx.direction,
    description: tx.description,
    counterpartyAccount: tx.counterpartyAccount ?? undefined,
    rawPayload: row.rawPayload,
  });

  await db
    .insert(casNormalizerLog)
    .values({
      id: generateSnowflake(),
      bankConnectionId,
      inboxEventId: BigInt(row.id),
      providerTxId: tx.externalTransactionId,
      providerTxHash: contentHash,
      bankTransactionId: BigInt(upsert.view.id),
      action: upsert.wasInserted ? "INSERT" : "SKIP_DUP",
    })
    .onConflictDoUpdate({
      target: [casNormalizerLog.bankConnectionId, casNormalizerLog.providerTxId],
      set: {
        inboxEventId: BigInt(row.id),
        bankTransactionId: BigInt(upsert.view.id),
        action: upsert.wasInserted ? "INSERT" : "SKIP_DUP",
        normalizedAt: new Date(),
      },
    });

  await completeCasInboxEvent(BigInt(row.id), row.leaseToken, BigInt(upsert.view.id));
  return "PROCESSED";
}

/**
 * Admin override (đằng sau endpoint expose:false) — xử lý ngay 1 dòng inbox
 * cụ thể theo id, bỏ qua next_attempt_at (nhưng vẫn tôn trọng lease đang giữ
 * bởi worker khác — FOR UPDATE SKIP LOCKED sẽ đơn giản không claim được nếu
 * đang bị lease, trả về claimed:0).
 */
export async function reprocessOneCasInboxEventService(id: bigint): Promise<ProcessCasInboxBatchResult> {
  const now = new Date();
  await db
    .update(schema.casSyncInbox)
    .set({ nextAttemptAt: now })
    .where(eq(schema.casSyncInbox.id, id));
  return processCasInboxBatch({ limit: 1, now });
}
