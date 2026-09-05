// F3 — chuẩn hoá 1 giao dịch thô Cas.so (từ webhook HOẶC từ 1 trang GET-poll)
// thành CanonicalBankTransaction, hoặc trả về typed reject. KHÔNG throw cho
// các lỗi dữ liệu nghiệp vụ (payload thiếu field) — throw chỉ dành cho lỗi
// lập trình/hạ tầng thật. Đây là hàm THUẦN (không đọc DB, không gọi network)
// để dễ test và dùng lại giống nhau ở cả đường webhook và đường poll.
import { createHash } from "node:crypto";
import { CAS_CONTRACT, type CasRawTransaction } from "./cas-contract";
import { parseDecimalToMoney } from "./money";

export type CanonicalBankTransaction = {
  workspaceId: string;
  bankConnectionId: string;
  externalTransactionId: string;
  bookedAt: string;
  amountMinor: string;
  currency: string;
  direction: "IN" | "OUT";
  counterpartyAccount: string | null;
  description: string;
  providerReference: string | null;
  rawPayloadRef: string;
  contractVersion: string;
};

export type NormalizeRejectReason =
  | "INVALID_PROVIDER_PAYLOAD" // thiếu/không hợp lệ amount, direction hoặc booked time
  | "NOT_A_TRANSACTION_EVENT" // envelope hợp lệ nhưng không phải sự kiện giao dịch (vd. grant.revoked)
  | "MALFORMED_RAW_PAYLOAD"; // raw không phải object / không parse được các field cơ bản

export type NormalizeCasTransactionResult =
  | { ok: true; transaction: CanonicalBankTransaction }
  | { ok: false; reason: NormalizeRejectReason; detail: string };

export interface NormalizerConnectionContext {
  id: string; // bankConnectionId
  workspaceId: string;
  providerEnvironment: string;
}

// Cas.so hiện chỉ có sandbox VN-bank; contract raw transaction (cas-contract.ts)
// không mang field currency riêng theo từng giao dịch. Đây là hằng số theo
// CONTRACT (không phải "default vì thiếu field nghiệp vụ" như amount/direction/
// time) nên không thuộc phạm vi cấm-default của F3.
const DEFAULT_CURRENCY = "VND";

/**
 * Identity dựng từ field contract-defined: connection (= grant+account 1:1
 * theo unique index migration 36) + transaction id + loại event + version
 * contract. KHÔNG dùng hash nguyên raw payload — 2 lần giao cùng 1 giao dịch
 * (webhook lẫn poll) có thể lệch byte (thêm field metadata, thứ tự khác...)
 * nhưng vẫn phải cùng identity để hội tụ về 1 canonical row.
 */
export function computeCasEventIdentity(p: {
  bankConnectionId: string | null; // null khi webhook chưa resolve được tenant
  bankSubAccId: string | null;
  externalTransactionId: string;
  eventKind: string; // 'transaction' | 'not_a_transaction' | ...
  contractVersion: string;
}): string {
  const connectionPart = p.bankConnectionId ?? `unresolved:${p.bankSubAccId ?? "unknown_account"}`;
  return [connectionPart, p.externalTransactionId, p.eventKind, p.contractVersion].join(":");
}

function isNonEmptyString(v: unknown): v is string {
  return typeof v === "string" && v.trim().length > 0;
}

/**
 * Trích externalTransactionId theo contract: ưu tiên `tid` (business tid),
 * fallback `id` (Cas.so internal numeric id) khi tid vắng.
 */
function extractExternalTransactionId(raw: Record<string, unknown>): string | null {
  if (isNonEmptyString(raw.tid)) return raw.tid;
  if (typeof raw.id === "number" && Number.isFinite(raw.id)) return String(raw.id);
  if (isNonEmptyString(raw.id)) return raw.id;
  return null;
}

export function normalizeCasTransaction(
  raw: unknown,
  verifiedContract: typeof CAS_CONTRACT,
  connection: NormalizerConnectionContext
): NormalizeCasTransactionResult {
  if (raw === null || typeof raw !== "object" || Array.isArray(raw)) {
    return {
      ok: false,
      reason: "MALFORMED_RAW_PAYLOAD",
      detail: "raw transaction payload is not an object",
    };
  }

  const rec = raw as Record<string, unknown>;

  const externalTransactionId = extractExternalTransactionId(rec);
  if (!externalTransactionId) {
    return {
      ok: false,
      reason: "INVALID_PROVIDER_PAYLOAD",
      detail: "missing transaction identifier (tid/id)",
    };
  }

  // amount — bắt buộc có, KHÔNG default 0. Số 0 không thể suy ra direction
  // (in/out) nên cũng bị coi là thiếu direction, không tự gán IN.
  const rawAmount = rec.amount;
  const amountPresent =
    (typeof rawAmount === "number" && Number.isFinite(rawAmount)) ||
    (typeof rawAmount === "string" && rawAmount.trim().length > 0);
  if (!amountPresent) {
    return {
      ok: false,
      reason: "INVALID_PROVIDER_PAYLOAD",
      detail: "missing amount",
    };
  }

  // direction — ưu tiên field explicit nếu provider có gửi (một số nguồn có
  // thể kèm 'direction' hoặc 'in'/'out' sau khi contract xác nhận thêm);
  // fallback: dấu của amount. amount === 0 -> không đủ để suy ra direction.
  let direction: "IN" | "OUT" | null = null;
  const explicitDirection = rec.direction;
  if (explicitDirection === "IN" || explicitDirection === "OUT") {
    direction = explicitDirection;
  } else {
    const numericAmount = typeof rawAmount === "number" ? rawAmount : Number(rawAmount);
    if (Number.isFinite(numericAmount) && numericAmount !== 0) {
      direction = numericAmount > 0 ? "IN" : "OUT";
    }
  }
  if (!direction) {
    return {
      ok: false,
      reason: "INVALID_PROVIDER_PAYLOAD",
      detail: "cannot determine direction (amount is zero/ambiguous and no explicit direction field)",
    };
  }

  // booked time — bắt buộc có và parse được, KHÔNG default now().
  const rawWhen = rec.when ?? rec.postedAt;
  if (!isNonEmptyString(rawWhen)) {
    return {
      ok: false,
      reason: "INVALID_PROVIDER_PAYLOAD",
      detail: "missing booked time (when)",
    };
  }
  const bookedAtMs = Date.parse(rawWhen);
  if (!Number.isFinite(bookedAtMs)) {
    return {
      ok: false,
      reason: "INVALID_PROVIDER_PAYLOAD",
      detail: `unparseable booked time: ${rawWhen}`,
    };
  }

  const currency = isNonEmptyString(rec.currency) ? rec.currency.toUpperCase() : DEFAULT_CURRENCY;

  let amountMinor: string;
  try {
    // IA13: KHÔNG được đi qua Number() khi rawAmount đã là string — JS number
    // (float64) chỉ chính xác tới 2^53, một amount string hợp lệ vượt
    // MAX_SAFE_INTEGER sẽ bị làm tròn sai trước khi tới parseDecimalToMoney
    // (vốn tự parse string bằng BigInt, không có giới hạn này). Chỉ strip dấu
    // âm trên string gốc, không Math.abs(Number(...)).
    const rawAmountStr = String(rawAmount).trim();
    const absAmountStr = rawAmountStr.replace(/^[+-]/, "");
    amountMinor = parseDecimalToMoney(absAmountStr, currency).minor;
  } catch (err: any) {
    return {
      ok: false,
      reason: "INVALID_PROVIDER_PAYLOAD",
      detail: `unparseable amount: ${String(rawAmount)} (${err?.message ?? err})`,
    };
  }

  const description = isNonEmptyString(rec.description) ? rec.description : "";
  const providerReference =
    typeof rec.id === "number" ? String(rec.id) : isNonEmptyString(rec.id) ? rec.id : null;
  const bankSubAccId = isNonEmptyString(rec.bank_sub_acc_id) ? rec.bank_sub_acc_id : null;

  const eventIdentity = computeCasEventIdentity({
    bankConnectionId: connection.id,
    bankSubAccId,
    externalTransactionId,
    eventKind: "transaction",
    contractVersion: verifiedContract.contractVersion,
  });

  return {
    ok: true,
    transaction: {
      workspaceId: connection.workspaceId,
      bankConnectionId: connection.id,
      externalTransactionId,
      bookedAt: new Date(bookedAtMs).toISOString(),
      amountMinor,
      currency,
      direction,
      counterpartyAccount: null, // contract raw không có field counterparty riêng — bank_sub_acc_id là account CHÍNH CHỦ, không phải đối tác
      description,
      providerReference,
      rawPayloadRef: `cas_sync_inbox:${eventIdentity}`,
      contractVersion: verifiedContract.contractVersion,
    },
  };
}

/**
 * Hash nội dung nghiệp vụ (không phải raw bytes) — dùng để phát hiện
 * correction/reversal: cùng provider_tx_id nhưng hash khác => nghi có sửa/
 * hoàn tác, KHÔNG tự overwrite record đã ghi, cần review (xem
 * cas_normalizer_log.action = 'CONFLICT').
 */
export function computeCanonicalContentHash(t: CanonicalBankTransaction): string {
  return createHash("sha256")
    .update(`${t.amountMinor}:${t.currency}:${t.direction}:${t.bookedAt}:${t.description}`)
    .digest("hex");
}

export type { CasRawTransaction };
