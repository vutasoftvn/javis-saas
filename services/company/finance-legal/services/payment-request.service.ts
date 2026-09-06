// F4 (docs/superpowers/plans/2026-09-05-business-agents-finance.md) — chỉ
// state machine đề nghị chi (payment_requests): create/update/submit/
// approve/reject/cancel/report-transfer. KHÔNG bao gồm: payment-qr.service.ts
// (VietQR — cần credential/contract xác nhận trước, cùng nguyên tắc đã áp
// dụng cho Cas.so ở F2/F3) và payment-allocation.service.ts (khớp
// bank_transaction, khoá thứ tự ID tránh deadlock, migrate dữ liệu đối soát
// cũ — việc riêng, phức tạp hơn). settlement_state vì vậy chỉ chuyển được
// UNPAID -> REPORTED ở đây; PARTIAL/PAID/EXCEPTION chờ payment-allocation.
import { APIError } from "encore.dev/api";
import { and, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { requireCommandAuthority } from "../../identity/services/command-authority.service";
import { computeCanonicalSha256 } from "./compliance/canonical-hasher";
import { requireFounderCommand } from "../../shared/auth/workspace-access";
import { computeProjectBudgetPosition } from "./budget-summary.service";

const { paymentRequests } = schema;

export interface PaymentRequestView {
  id: string;
  workspaceId: string;
  legalEntityId: string;
  projectId: string | null;
  ownerMemberId: string | null;
  amountMinor: string;
  currency: string;
  beneficiaryBankBin: string;
  beneficiaryAccountNumber: string;
  beneficiaryName: string;
  purpose: string;
  documentRefs: string[];
  dueAt: string | null;
  transferReference: string | null;
  approvalState: string;
  settlementState: string;
  accountingState: string;
  version: number;
  approvalHash: string | null;
  approvedVersion: number | null;
  approvedByMemberId: string | null;
  approvedAt: string | null;
  reportedByMemberId: string | null;
  reportedAt: string | null;
  idempotencyKey: string;
  createdAt: string;
  updatedAt: string;
  budgetOverrideReason: string | null;
  budgetOverrideByMemberId: string | null;
}

function toView(r: typeof paymentRequests.$inferSelect): PaymentRequestView {
  return {
    id: String(r.id),
    workspaceId: String(r.workspaceId),
    legalEntityId: String(r.legalEntityId),
    projectId: r.projectId ? String(r.projectId) : null,
    ownerMemberId: r.ownerMemberId ? String(r.ownerMemberId) : null,
    amountMinor: r.amountMinor,
    currency: r.currency,
    beneficiaryBankBin: r.beneficiaryBankBin,
    beneficiaryAccountNumber: r.beneficiaryAccountNumber,
    beneficiaryName: r.beneficiaryName,
    purpose: r.purpose,
    documentRefs: (r.documentRefs as string[]) || [],
    dueAt: r.dueAt ? r.dueAt.toISOString() : null,
    transferReference: r.transferReference,
    approvalState: r.approvalState,
    settlementState: r.settlementState,
    accountingState: r.accountingState,
    version: r.version,
    approvalHash: r.approvalHash,
    approvedVersion: r.approvedVersion,
    approvedByMemberId: r.approvedByMemberId ? String(r.approvedByMemberId) : null,
    approvedAt: r.approvedAt ? r.approvedAt.toISOString() : null,
    reportedByMemberId: r.reportedByMemberId ? String(r.reportedByMemberId) : null,
    reportedAt: r.reportedAt ? r.reportedAt.toISOString() : null,
    idempotencyKey: r.idempotencyKey,
    createdAt: r.createdAt.toISOString(),
    updatedAt: r.updatedAt.toISOString(),
    budgetOverrideReason: r.budgetOverrideReason ?? null,
    budgetOverrideByMemberId: r.budgetOverrideByMemberId ? String(r.budgetOverrideByMemberId) : null,
  };
}

function computeApprovalHash(r: {
  workspaceId: string;
  legalEntityId: string;
  requestId: string;
  version: number;
  beneficiaryBankBin: string;
  beneficiaryAccountNumber: string;
  beneficiaryName: string;
  amountMinor: string;
  currency: string;
  transferReference: string | null;
}): string {
  return computeCanonicalSha256({
    workspaceId: r.workspaceId,
    legalEntityId: r.legalEntityId,
    requestId: r.requestId,
    version: r.version,
    beneficiary: {
      bankBin: r.beneficiaryBankBin,
      accountNumber: r.beneficiaryAccountNumber,
      name: r.beneficiaryName,
    },
    amountMinor: r.amountMinor,
    currency: r.currency,
    transferReference: r.transferReference,
  });
}

async function loadOwnRequest(wsId: bigint, id: bigint) {
  const [row] = await db
    .select()
    .from(paymentRequests)
    .where(and(eq(paymentRequests.id, id), eq(paymentRequests.workspaceId, wsId), isNull(paymentRequests.deletedAt)));
  if (!row) {
    throw APIError.notFound(`Payment request ${id} not found`);
  }
  return row;
}

export interface CreatePaymentRequestInput {
  legalEntityId: string;
  projectId?: string;
  amountMinor: string;
  currency: string;
  beneficiaryBankBin: string;
  beneficiaryAccountNumber: string;
  beneficiaryName: string;
  purpose: string;
  documentRefs?: string[];
  dueAt?: string;
  transferReference?: string;
  idempotencyKey: string;
}

/**
 * Tạo đề nghị chi ở trạng thái DRAFT. Idempotent theo (workspace,
 * idempotencyKey) — gọi lại với cùng key trả về bản ghi đã có, không tạo
 * trùng (founder/agent retry sau timeout mạng không tạo 2 đề nghị chi).
 */
export async function createPaymentRequestService(
  ctx: TenantContext,
  input: CreatePaymentRequestInput
): Promise<PaymentRequestView> {
  await requireCommandAuthority(ctx, "finance.request.create", {
    workspaceId: ctx.workspaceId,
    legalEntityId: input.legalEntityId,
    projectId: input.projectId,
  });

  const wsId = BigInt(ctx.workspaceId);

  const amount = BigInt(input.amountMinor);
  if (amount <= 0n) {
    throw APIError.invalidArgument("amountMinor must be a positive integer");
  }

  const [existing] = await db
    .select()
    .from(paymentRequests)
    .where(and(eq(paymentRequests.workspaceId, wsId), eq(paymentRequests.idempotencyKey, input.idempotencyKey)));
  if (existing) {
    return toView(existing);
  }

  const id = generateSnowflake();
  const [created] = await db
    .insert(paymentRequests)
    .values({
      id,
      workspaceId: wsId,
      legalEntityId: BigInt(input.legalEntityId),
      projectId: input.projectId ? BigInt(input.projectId) : null,
      ownerMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
      amountMinor: input.amountMinor,
      currency: input.currency.toUpperCase(),
      beneficiaryBankBin: input.beneficiaryBankBin,
      beneficiaryAccountNumber: input.beneficiaryAccountNumber,
      beneficiaryName: input.beneficiaryName,
      purpose: input.purpose,
      documentRefs: input.documentRefs ?? [],
      dueAt: input.dueAt ? new Date(input.dueAt) : null,
      transferReference: input.transferReference ?? null,
      idempotencyKey: input.idempotencyKey,
      createdBy: ctx.userId ? BigInt(ctx.userId) : null,
    })
    .onConflictDoNothing({
      target: [paymentRequests.workspaceId, paymentRequests.idempotencyKey],
    })
    .returning();

  if (created) {
    return toView(created);
  }

  // Conflict thắng bởi 1 request đồng thời khác cùng idempotencyKey.
  const [raced] = await db
    .select()
    .from(paymentRequests)
    .where(and(eq(paymentRequests.workspaceId, wsId), eq(paymentRequests.idempotencyKey, input.idempotencyKey)));
  return toView(raced);
}

export interface UpdatePaymentRequestInput {
  id: string;
  expectedVersion: number;
  amountMinor?: string;
  beneficiaryBankBin?: string;
  beneficiaryAccountNumber?: string;
  beneficiaryName?: string;
  purpose?: string;
  documentRefs?: string[];
  dueAt?: string | null;
  transferReference?: string | null;
}

const TERMINAL_APPROVAL_STATES = new Set(["REJECTED", "CANCELLED"]);
const BENEFICIARY_AFFECTING_FIELDS = [
  "amountMinor",
  "beneficiaryBankBin",
  "beneficiaryAccountNumber",
  "beneficiaryName",
] as const;

/**
 * Sửa đề nghị chi (chỉ các field trước khi thanh toán). Nếu request đã
 * APPROVED và field ảnh hưởng thanh toán (số tiền/người thụ hưởng) thay đổi,
 * proof duyệt cũ hết hiệu lực — quay lại DRAFT, xoá approval_hash/
 * approved_version/approved_by/approved_at, cần duyệt lại từ đầu.
 */
export async function updatePaymentRequestService(
  ctx: TenantContext,
  input: UpdatePaymentRequestInput
): Promise<PaymentRequestView> {
  await requireCommandAuthority(ctx, "finance.request.create", { workspaceId: ctx.workspaceId });

  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(input.id);
  const current = await loadOwnRequest(wsId, id);

  if (TERMINAL_APPROVAL_STATES.has(current.approvalState)) {
    throw APIError.failedPrecondition(
      `Cannot edit a payment request in terminal state ${current.approvalState}`
    );
  }
  if (current.settlementState !== "UNPAID") {
    throw APIError.failedPrecondition(
      `Cannot edit a payment request once settlement has started (settlementState=${current.settlementState})`
    );
  }
  if (current.version !== input.expectedVersion) {
    const err = APIError.aborted(
      `CAS mismatch: expected version ${input.expectedVersion} but current is ${current.version}`
    );
    (err as any).code = "CONCURRENT_MODIFICATION";
    throw err;
  }

  const beneficiaryFieldChanged = BENEFICIARY_AFFECTING_FIELDS.some(
    (f) => input[f] !== undefined && String(input[f]) !== String((current as any)[f])
  );
  const wasApproved = current.approvalState === "APPROVED";

  const nextVersion = current.version + 1;
  const [updated] = await db
    .update(paymentRequests)
    .set({
      amountMinor: input.amountMinor ?? current.amountMinor,
      beneficiaryBankBin: input.beneficiaryBankBin ?? current.beneficiaryBankBin,
      beneficiaryAccountNumber: input.beneficiaryAccountNumber ?? current.beneficiaryAccountNumber,
      beneficiaryName: input.beneficiaryName ?? current.beneficiaryName,
      purpose: input.purpose ?? current.purpose,
      documentRefs: input.documentRefs ?? current.documentRefs,
      dueAt: input.dueAt !== undefined ? (input.dueAt ? new Date(input.dueAt) : null) : current.dueAt,
      transferReference:
        input.transferReference !== undefined ? input.transferReference : current.transferReference,
      version: nextVersion,
      // IA-style fail-closed: sửa field ảnh hưởng thanh toán trên request đã
      // APPROVED phải làm mất hiệu lực duyệt cũ, không được giữ nguyên
      // approval_hash/approvalState cho dữ liệu đã đổi.
      approvalState: wasApproved && beneficiaryFieldChanged ? "DRAFT" : current.approvalState,
      approvalHash: wasApproved && beneficiaryFieldChanged ? null : current.approvalHash,
      approvedVersion: wasApproved && beneficiaryFieldChanged ? null : current.approvedVersion,
      approvedByMemberId: wasApproved && beneficiaryFieldChanged ? null : current.approvedByMemberId,
      approvedAt: wasApproved && beneficiaryFieldChanged ? null : current.approvedAt,
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(paymentRequests.id, id),
        eq(paymentRequests.workspaceId, wsId),
        eq(paymentRequests.version, current.version)
      )
    )
    .returning();

  if (!updated) {
    const err = APIError.aborted("Concurrent modification during payment request update");
    (err as any).code = "CONCURRENT_MODIFICATION";
    throw err;
  }

  return toView(updated);
}

async function transitionApprovalState(
  wsId: bigint,
  id: bigint,
  expectedVersion: number,
  fromStates: string[],
  toState: string,
  extra?: Partial<typeof paymentRequests.$inferInsert>
) {
  const current = await loadOwnRequest(wsId, id);
  if (current.version !== expectedVersion) {
    const err = APIError.aborted(
      `CAS mismatch: expected version ${expectedVersion} but current is ${current.version}`
    );
    (err as any).code = "CONCURRENT_MODIFICATION";
    throw err;
  }
  if (!fromStates.includes(current.approvalState)) {
    throw APIError.invalidArgument(
      `Invalid payment request transition from ${current.approvalState} to ${toState}`
    );
  }

  const [updated] = await db
    .update(paymentRequests)
    .set({
      approvalState: toState,
      version: current.version + 1,
      updatedAt: new Date(),
      ...extra,
    })
    .where(
      and(
        eq(paymentRequests.id, id),
        eq(paymentRequests.workspaceId, wsId),
        eq(paymentRequests.version, current.version)
      )
    )
    .returning();

  if (!updated) {
    const err = APIError.aborted("Concurrent modification during payment request transition");
    (err as any).code = "CONCURRENT_MODIFICATION";
    throw err;
  }
  return updated;
}

export async function submitPaymentRequestService(
  ctx: TenantContext,
  p: { id: string; expectedVersion: number }
): Promise<PaymentRequestView> {
  await requireCommandAuthority(ctx, "finance.request.create", { workspaceId: ctx.workspaceId });
  const updated = await transitionApprovalState(
    BigInt(ctx.workspaceId),
    BigInt(p.id),
    p.expectedVersion,
    ["DRAFT"],
    "SUBMITTED"
  );
  return toView(updated);
}

/**
 * Duyệt đề nghị chi — hành động tài chính rủi ro cao (CLAUDE.md quy tắc 8):
 * bắt buộc requireCommandAuthority với facts.amount để rule có hạn mức
 * (maxAmountMinor/currency, xem permission-evaluator.ts) áp dụng đúng, KHÔNG
 * chỉ kiểm role trần. Sau APPROVED: chỉ tạo QR (chưa xây ở đây), KHÔNG được
 * coi là đã thanh toán — settlementState giữ nguyên UNPAID.
 */
export async function approvePaymentRequestService(
  ctx: TenantContext,
  p: { id: string; expectedVersion: number; overrideReason?: string }
): Promise<PaymentRequestView> {
  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(p.id);
  const current = await loadOwnRequest(wsId, id);

  await requireCommandAuthority(
    ctx,
    "finance.request.approve",
    { workspaceId: ctx.workspaceId, legalEntityId: String(current.legalEntityId), projectId: current.projectId ? String(current.projectId) : undefined },
    { amount: { minor: current.amountMinor, currency: current.currency } }
  );

  return db.transaction(async (tx) => {
    if (current.version !== p.expectedVersion) {
      const err = APIError.aborted(
        `CAS mismatch: expected version ${p.expectedVersion} but current is ${current.version}`
      );
      (err as any).code = "CONCURRENT_MODIFICATION";
      throw err;
    }
    if (current.approvalState !== "SUBMITTED") {
      throw APIError.invalidArgument(
        `Invalid payment request transition from ${current.approvalState} to APPROVED`
      );
    }

    const nextVersion = current.version + 1;
    let budgetOverrideReason: string | null = null;
    let budgetOverrideByMemberId: bigint | null = null;

    if (current.projectId) {
      const position = await computeProjectBudgetPosition(
        tx,
        {
          workspaceId: String(current.workspaceId),
          projectId: String(current.projectId),
          currency: current.currency,
          asOf: new Date(),
        },
        true
      );

      if (position.coverage === "COMPLETE") {
        const wouldBeTotal = position.committedUnpaidMinor + position.actualPaidMinor + BigInt(current.amountMinor);
        if (wouldBeTotal > position.limitMinor) {
          try {
            requireFounderCommand(ctx, "finance.budget.override");
          } catch {
            throw APIError.failedPrecondition(
              "BUDGET_LIMIT_EXCEEDED: chỉ founder mới có thể duyệt vượt ngân sách"
            );
          }
          if (!p.overrideReason?.trim()) {
            throw APIError.failedPrecondition(
              "BUDGET_LIMIT_EXCEEDED: cần overrideReason khi duyệt vượt ngân sách"
            );
          }
          budgetOverrideReason = p.overrideReason.trim();
          budgetOverrideByMemberId = BigInt(ctx.workforceMemberId ?? ctx.userId);
        }
      }
    }

    const approvalHash = computeApprovalHash({
      workspaceId: String(current.workspaceId),
      legalEntityId: String(current.legalEntityId),
      requestId: String(current.id),
      version: nextVersion,
      beneficiaryBankBin: current.beneficiaryBankBin,
      beneficiaryAccountNumber: current.beneficiaryAccountNumber,
      beneficiaryName: current.beneficiaryName,
      amountMinor: current.amountMinor,
      currency: current.currency,
      transferReference: current.transferReference,
    });

    const now = new Date();
    const [updated] = await tx
      .update(paymentRequests)
      .set({
        approvalState: "APPROVED",
        version: nextVersion,
        approvalHash,
        approvedVersion: nextVersion,
        approvedByMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
        approvedAt: now,
        updatedAt: now,
        budgetOverrideReason,
        budgetOverrideByMemberId,
      })
      .where(
        and(
          eq(paymentRequests.id, id),
          eq(paymentRequests.workspaceId, wsId),
          eq(paymentRequests.version, current.version)
        )
      )
      .returning();

    if (!updated) {
      const err = APIError.aborted("Concurrent modification during payment request approval");
      (err as any).code = "CONCURRENT_MODIFICATION";
      throw err;
    }

    return toView(updated);
  });
}

export async function rejectPaymentRequestService(
  ctx: TenantContext,
  p: { id: string; expectedVersion: number; reason: string }
): Promise<PaymentRequestView> {
  if (!p.reason || !p.reason.trim()) {
    throw APIError.invalidArgument("Rejecting a payment request requires a reason");
  }
  await requireCommandAuthority(ctx, "finance.request.approve", { workspaceId: ctx.workspaceId });
  const updated = await transitionApprovalState(
    BigInt(ctx.workspaceId),
    BigInt(p.id),
    p.expectedVersion,
    ["SUBMITTED"],
    "REJECTED"
  );
  return toView(updated);
}

export async function cancelPaymentRequestService(
  ctx: TenantContext,
  p: { id: string; expectedVersion: number }
): Promise<PaymentRequestView> {
  await requireCommandAuthority(ctx, "finance.request.approve", { workspaceId: ctx.workspaceId });

  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(p.id);
  const current = await loadOwnRequest(wsId, id);
  if (current.settlementState !== "UNPAID") {
    // Đã REPORTED (founder tự báo đã chuyển) hoặc xa hơn (PARTIAL/PAID/
    // EXCEPTION) — tiền coi như đã/đang được gửi thật, "cancel" đề nghị chi
    // không có ý nghĩa hoàn tác giao dịch đã xảy ra.
    throw APIError.failedPrecondition(
      `Cannot cancel a payment request once settlement has started (settlementState=${current.settlementState})`
    );
  }

  const updated = await transitionApprovalState(
    wsId,
    id,
    p.expectedVersion,
    ["DRAFT", "SUBMITTED", "APPROVED"],
    "CANCELLED"
  );
  return toView(updated);
}

/**
 * Founder tự báo đã chuyển khoản (chưa đối soát với bank_transaction thật —
 * đó là việc của payment-allocation.service.ts, chưa xây). Chỉ đổi
 * settlementState UNPAID -> REPORTED, KHÔNG coi là PAID.
 */
export async function reportPaymentTransferService(
  ctx: TenantContext,
  p: { id: string; expectedVersion: number }
): Promise<PaymentRequestView> {
  await requireCommandAuthority(ctx, "finance.request.create", { workspaceId: ctx.workspaceId });

  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(p.id);
  const current = await loadOwnRequest(wsId, id);

  if (current.version !== p.expectedVersion) {
    const err = APIError.aborted(
      `CAS mismatch: expected version ${p.expectedVersion} but current is ${current.version}`
    );
    (err as any).code = "CONCURRENT_MODIFICATION";
    throw err;
  }
  if (current.approvalState !== "APPROVED") {
    throw APIError.failedPrecondition(
      `Cannot report transfer for a payment request that is not APPROVED (approvalState=${current.approvalState})`
    );
  }
  // Approval hash phải còn khớp version hiện tại — nếu request bị sửa sau
  // approve (quay lại DRAFT), approvalState đã không còn APPROVED nên nhánh
  // này không tới được; giữ check tường minh để không im lặng tin sai.
  if (current.approvedVersion !== current.version) {
    throw APIError.failedPrecondition("Approval proof is stale for the current version");
  }
  if (current.settlementState !== "UNPAID") {
    throw APIError.invalidArgument(
      `Invalid settlement transition from ${current.settlementState} to REPORTED`
    );
  }

  const now = new Date();
  const [updated] = await db
    .update(paymentRequests)
    .set({
      settlementState: "REPORTED",
      reportedByMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
      reportedAt: now,
      version: current.version + 1,
      updatedAt: now,
    })
    .where(
      and(
        eq(paymentRequests.id, id),
        eq(paymentRequests.workspaceId, wsId),
        eq(paymentRequests.version, current.version)
      )
    )
    .returning();

  if (!updated) {
    const err = APIError.aborted("Concurrent modification during report-transfer");
    (err as any).code = "CONCURRENT_MODIFICATION";
    throw err;
  }

  return toView(updated);
}

export async function getPaymentRequestService(
  ctx: TenantContext,
  id: string
): Promise<PaymentRequestView> {
  const row = await loadOwnRequest(BigInt(ctx.workspaceId), BigInt(id));
  return toView(row);
}

export async function listPaymentRequestsService(
  ctx: TenantContext,
  filter?: { legalEntityId?: string; approvalState?: string }
): Promise<PaymentRequestView[]> {
  const wsId = BigInt(ctx.workspaceId);
  const conditions = [eq(paymentRequests.workspaceId, wsId), isNull(paymentRequests.deletedAt)];
  if (filter?.legalEntityId) {
    conditions.push(eq(paymentRequests.legalEntityId, BigInt(filter.legalEntityId)));
  }
  if (filter?.approvalState) {
    conditions.push(eq(paymentRequests.approvalState, filter.approvalState));
  }
  const rows = await db
    .select()
    .from(paymentRequests)
    .where(and(...conditions));
  return rows.map(toView);
}
