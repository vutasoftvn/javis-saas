// F4 phần 2 — khớp payment_requests đã APPROVED với bank_transactions thật
// (đối soát). KHÔNG bao gồm: migrate dữ liệu document_reconciliation_proposals
// cũ sang allocation (cần đánh giá dữ liệu lịch sử thật theo từng workspace,
// không đoán mapping tự động).
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { requireCommandAuthority } from "../../identity/services/command-authority.service";
import { parseDecimalToMoney } from "./money";

const { paymentAllocations, paymentRequests, bankTransactions } = schema;

export interface PaymentAllocationView {
  id: string;
  workspaceId: string;
  bankTransactionId: string;
  requestId: string;
  amountMinor: string;
  currency: string;
  status: "ACTIVE" | "REVERSED";
  reversedReason: string | null;
  reversedByMemberId: string | null;
  reversedAt: string | null;
  idempotencyKey: string;
  createdAt: string;
}

function toView(r: typeof paymentAllocations.$inferSelect): PaymentAllocationView {
  return {
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    bankTransactionId: String(r.bankTransactionId),
    requestId: String(r.requestId),
    amountMinor: r.amountMinor,
    currency: r.currency,
    status: r.status as "ACTIVE" | "REVERSED",
    reversedReason: r.reversedReason,
    reversedByMemberId: r.reversedByMemberId ? String(r.reversedByMemberId) : null,
    reversedAt: r.reversedAt ? r.reversedAt.toISOString() : null,
    idempotencyKey: r.idempotencyKey,
    createdAt: r.createdAt.toISOString(),
  };
}

async function sumActiveAllocations(
  tx: any,
  field: "bankTransactionId" | "requestId",
  value: bigint
): Promise<bigint> {
  const rows = await tx
    .select({ amountMinor: paymentAllocations.amountMinor })
    .from(paymentAllocations)
    .where(and(eq(paymentAllocations[field], value), eq(paymentAllocations.status, "ACTIVE")));
  return rows.reduce((acc: bigint, r: { amountMinor: string }) => acc + BigInt(r.amountMinor), 0n);
}

export interface CreatePaymentAllocationInput {
  requestId: string;
  bankTransactionId: string;
  amountMinor: string;
  idempotencyKey: string;
}

/**
 * Khớp 1 phần hoặc toàn bộ payment_request với 1 bank_transaction thật.
 * Khoá payment_request + bank_transaction theo THỨ TỰ ID (không phải luôn
 * request-trước hay bank-trước) để 2 giao dịch đồng thời không deadlock lẫn
 * nhau (theo đúng pseudocode trong plan F4).
 */
export async function createPaymentAllocationService(
  ctx: TenantContext,
  input: CreatePaymentAllocationInput
): Promise<PaymentAllocationView> {
  await requireCommandAuthority(ctx, "finance.reconcile", { workspaceId: ctx.workspaceId });

  const wsId = BigInt(ctx.workspaceId);
  const amount = BigInt(input.amountMinor);
  if (amount <= 0n) {
    throw APIError.invalidArgument("amountMinor must be a positive integer");
  }

  return db.transaction(async (tx) => {
    const [existing] = await tx
      .select()
      .from(paymentAllocations)
      .where(and(eq(paymentAllocations.workspaceId, wsId), eq(paymentAllocations.idempotencyKey, input.idempotencyKey)));
    if (existing) {
      return toView(existing);
    }

    const requestIdBig = BigInt(input.requestId);
    const bankTxnIdBig = BigInt(input.bankTransactionId);

    // Khoá theo thứ tự ID tăng dần — không cố định "request trước" hay
    // "bank transaction trước" — để mọi transaction đồng thời cùng thống
    // nhất 1 thứ tự khoá, tránh deadlock vòng tròn.
    let request: typeof paymentRequests.$inferSelect | undefined;
    let bankTxn: typeof bankTransactions.$inferSelect | undefined;
    if (requestIdBig < bankTxnIdBig) {
      [request] = await tx
        .select()
        .from(paymentRequests)
        .where(and(eq(paymentRequests.id, requestIdBig), eq(paymentRequests.workspaceId, wsId)))
        .for("update");
      [bankTxn] = await tx
        .select()
        .from(bankTransactions)
        .where(and(eq(bankTransactions.id, bankTxnIdBig), eq(bankTransactions.workspaceId, wsId)))
        .for("update");
    } else {
      [bankTxn] = await tx
        .select()
        .from(bankTransactions)
        .where(and(eq(bankTransactions.id, bankTxnIdBig), eq(bankTransactions.workspaceId, wsId)))
        .for("update");
      [request] = await tx
        .select()
        .from(paymentRequests)
        .where(and(eq(paymentRequests.id, requestIdBig), eq(paymentRequests.workspaceId, wsId)))
        .for("update");
    }

    if (!request) {
      throw APIError.notFound(`Payment request ${input.requestId} not found`);
    }
    if (!bankTxn) {
      throw APIError.notFound(`Bank transaction ${input.bankTransactionId} not found`);
    }

    if (request.approvalState !== "APPROVED") {
      throw APIError.failedPrecondition(
        `Cannot allocate against a payment request that is not APPROVED (approvalState=${request.approvalState})`
      );
    }
    if (request.approvedVersion !== request.version) {
      throw APIError.failedPrecondition("Approval proof is stale for the current version");
    }
    if (bankTxn.direction !== "OUT") {
      throw APIError.invalidArgument(
        `Cannot allocate a payment request against an ${bankTxn.direction} bank transaction (must be OUT)`
      );
    }
    if (bankTxn.currency.toUpperCase() !== request.currency.toUpperCase()) {
      throw APIError.invalidArgument(
        `Currency mismatch: request is ${request.currency}, bank transaction is ${bankTxn.currency}`
      );
    }

    // bank_transactions.amount là DECIMAL (scale 2), payment_requests.amount_minor
    // là minor units nguyên — quy đổi qua Money helper (IA13 pattern), không
    // tự trừ/so sánh 2 đơn vị khác nhau.
    const bankAmountMinor = BigInt(parseDecimalToMoney(bankTxn.amount, bankTxn.currency).minor);

    const bankAllocated = await sumActiveAllocations(tx, "bankTransactionId", bankTxnIdBig);
    const bankRemaining = bankAmountMinor - bankAllocated;

    const requestAllocated = await sumActiveAllocations(tx, "requestId", requestIdBig);
    const requestRemainder = BigInt(request.amountMinor) - requestAllocated;

    if (amount > bankRemaining || amount > requestRemainder) {
      const err = APIError.failedPrecondition(
        `Allocation of ${amount} exceeds available remainder (bankRemaining=${bankRemaining}, requestRemainder=${requestRemainder})`
      );
      (err as any).code = "ALLOCATION_EXCEEDED";
      throw err;
    }

    const id = generateSnowflake();
    const [created] = await tx
      .insert(paymentAllocations)
      .values({
        id,
        workspaceId: wsId,
        bankTransactionId: bankTxnIdBig,
        requestId: requestIdBig,
        amountMinor: input.amountMinor,
        currency: request.currency,
        idempotencyKey: input.idempotencyKey,
        createdBy: ctx.userId ? BigInt(ctx.userId) : null,
      })
      .onConflictDoNothing({ target: [paymentAllocations.workspaceId, paymentAllocations.idempotencyKey] })
      .returning();

    if (!created) {
      const [raced] = await tx
        .select()
        .from(paymentAllocations)
        .where(and(eq(paymentAllocations.workspaceId, wsId), eq(paymentAllocations.idempotencyKey, input.idempotencyKey)));
      return toView(raced);
    }

    const nextRemaining = requestRemainder - amount;
    const newSettlementState = nextRemaining === 0n ? "PAID" : "PARTIAL";
    await tx
      .update(paymentRequests)
      .set({ settlementState: newSettlementState, updatedAt: new Date() })
      .where(and(eq(paymentRequests.id, requestIdBig), eq(paymentRequests.workspaceId, wsId)));

    return toView(created);
  });
}

export interface ReversePaymentAllocationInput {
  allocationId: string;
  reason: string;
}

/**
 * Đảo 1 allocation — KHÔNG xoá lịch sử (giữ nguyên bản ghi, chỉ đổi status
 * sang REVERSED + lý do/actor/thời điểm). Đưa request về EXCEPTION khi
 * không còn allocation ACTIVE nào (cần người xem lại tại sao 1 khoản đã
 * "khớp" giờ không còn khớp nữa, KHÔNG âm thầm coi như chưa từng thanh
 * toán).
 */
export async function reversePaymentAllocationService(
  ctx: TenantContext,
  input: ReversePaymentAllocationInput
): Promise<PaymentAllocationView> {
  await requireCommandAuthority(ctx, "finance.reconcile", { workspaceId: ctx.workspaceId });

  if (!input.reason || !input.reason.trim()) {
    throw APIError.invalidArgument("Reversing an allocation requires a reason");
  }

  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(input.allocationId);

  return db.transaction(async (tx) => {
    const [alloc] = await tx
      .select()
      .from(paymentAllocations)
      .where(and(eq(paymentAllocations.id, id), eq(paymentAllocations.workspaceId, wsId)))
      .for("update");
    if (!alloc) {
      throw APIError.notFound(`Payment allocation ${input.allocationId} not found`);
    }
    if (alloc.status !== "ACTIVE") {
      throw APIError.failedPrecondition(`Allocation ${input.allocationId} is already REVERSED`);
    }

    const now = new Date();
    const [updated] = await tx
      .update(paymentAllocations)
      .set({
        status: "REVERSED",
        reversedReason: input.reason,
        reversedByMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
        reversedAt: now,
      })
      .where(and(eq(paymentAllocations.id, id), eq(paymentAllocations.status, "ACTIVE")))
      .returning();

    if (!updated) {
      const err = APIError.aborted("Concurrent modification during allocation reversal");
      (err as any).code = "CONCURRENT_MODIFICATION";
      throw err;
    }

    const [request] = await tx
      .select()
      .from(paymentRequests)
      .where(and(eq(paymentRequests.id, alloc.requestId), eq(paymentRequests.workspaceId, wsId)))
      .for("update");
    if (request) {
      const remainingActive = await sumActiveAllocations(tx, "requestId", alloc.requestId);
      const newSettlementState = remainingActive === 0n ? "EXCEPTION" : "PARTIAL";
      await tx
        .update(paymentRequests)
        .set({ settlementState: newSettlementState, updatedAt: now })
        .where(and(eq(paymentRequests.id, alloc.requestId), eq(paymentRequests.workspaceId, wsId)));
    }

    return toView(updated);
  });
}

export async function listPaymentAllocationsService(
  ctx: TenantContext,
  filter: { requestId?: string; bankTransactionId?: string }
): Promise<PaymentAllocationView[]> {
  const wsId = BigInt(ctx.workspaceId);
  const conditions = [eq(paymentAllocations.workspaceId, wsId)];
  if (filter.requestId) {
    conditions.push(eq(paymentAllocations.requestId, BigInt(filter.requestId)));
  }
  if (filter.bankTransactionId) {
    conditions.push(eq(paymentAllocations.bankTransactionId, BigInt(filter.bankTransactionId)));
  }
  const rows = await db
    .select()
    .from(paymentAllocations)
    .where(and(...conditions));
  return rows.map(toView);
}
