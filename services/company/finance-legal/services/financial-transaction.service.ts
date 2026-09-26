import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspaceRecord } from "../../identity/services/workspace.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { AGENT_CAP } from "../../shared/auth/agent-capabilities";
import { requireCommandAuthority } from "../../identity/services/command-authority.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { assertOpenPostingPeriod } from "./posting-guard.service";
import { assertProjectInWorkspace } from "./budget-summary.service";

const { financialTransactions } = schema;

export type ApprovalStatus = "AUTO_APPROVED" | "PENDING_APPROVAL" | "APPROVED";

/**
 * Ngưỡng số tiền (VND) mà từ đó một giao dịch OUT (tiền ra) bắt buộc phải có
 * người có quyền founder/co-founder duyệt trước khi được tính là chính thức.
 * Giao dịch dưới ngưỡng hoặc chiều IN được tự động duyệt (rủi ro thấp).
 */
export const FINANCIAL_TRANSACTION_APPROVAL_THRESHOLD = Number(
  process.env.FINANCIAL_TRANSACTION_APPROVAL_THRESHOLD_VND || "10000000"
);

export interface FinancialTransaction {
  id: string;
  workspaceId: string;
  legalEntityId: string | null;
  documentId: string | null;
  projectId: string | null;
  cycleId: string | null;
  workItemId: string | null;
  idempotencyKey: string | null;
  transactionDate: string;
  description: string;
  amount: string;
  currency: string;
  direction: "IN" | "OUT";
  category: string | null;
  approvalStatus: ApprovalStatus;
  approvedByUserId: string | null;
  approvedAt: string | null;
  createdAt: string;
}

export interface RecordFinancialTransactionParams {
  workspaceId: string;
  legalEntityId?: string;
  projectId?: string;
  transactionDate: string;
  description: string;
  amount: string;
  currency?: string;
  direction: "IN" | "OUT";
  category?: string;
  workItemId?: string;
  idempotencyKey?: string;
  authorization?: string;
}

export interface ApproveFinancialTransactionParams {
  id: string;
  ctx: TenantContext;
}

function requiresApproval(direction: "IN" | "OUT", amount: string): boolean {
  if (direction !== "OUT") return false;
  return Math.abs(Number(amount)) >= FINANCIAL_TRANSACTION_APPROVAL_THRESHOLD;
}

function toFinancialTransaction(row: typeof financialTransactions.$inferSelect): FinancialTransaction {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    legalEntityId: row.legalEntityId ? String(row.legalEntityId) : null,
    documentId: row.documentId ? String(row.documentId) : null,
    projectId: row.projectId ? String(row.projectId) : null,
    cycleId: row.cycleId ? String(row.cycleId) : null,
    workItemId: row.workItemId ? String(row.workItemId) : null,
    idempotencyKey: row.idempotencyKey,
    transactionDate: String(row.transactionDate),
    description: row.description,
    amount: row.amount,
    currency: row.currency || "VND",
    direction: row.direction as "IN" | "OUT",
    category: row.category,
    approvalStatus: row.approvalStatus as ApprovalStatus,
    approvedByUserId: row.approvedByUserId ? String(row.approvedByUserId) : null,
    approvedAt: row.approvedAt ? row.approvedAt.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}

/**
 * Cổng quyền tường minh cho việc ghi nhận giao dịch tài chính — trước đây
 * `recordFinancialTransactionService` chỉ kiểm tra caller là member của
 * workspace (`requireWorkspaceAccess`, mọi role kể cả auditor/read-only đều
 * qua được) mà không có bước xét quyền command nào riêng cho hành động ghi
 * sổ. Helper này thêm bước xét quyền `finance.transaction.record` qua
 * catalog + role assignments (founder được default-allow, member/auditor
 * thường phải có role assignment cấp quyền rõ ràng mới qua).
 *
 * `requireCommandAuthority` -> `requireBusinessAction` (business-authorization.service.ts)
 * đã tự throw APIError.permissionDenied khi quyết định là DENY, và
 * APIError.failedPrecondition (code APPROVAL_REQUIRED) khi catalog quyết
 * định REQUIRE_APPROVAL — helper này không bắt lại các lỗi đó, để nguyên
 * hành vi chuẩn đã dùng ở payment-request.service.ts. REQUIRE_APPROVAL ở
 * đây là khái niệm khác với ngưỡng duyệt số tiền (`requiresApproval`/
 * FINANCIAL_TRANSACTION_APPROVAL_THRESHOLD) bên dưới — ngưỡng số tiền vẫn
 * giữ nguyên logic cũ, không bị thay thế bởi cổng quyền command này.
 */
export async function requireFinancialTransactionWrite(
  authorization: string | undefined,
  workspaceId: string
): Promise<TenantContext> {
  const ctx = await requireWorkspaceAccess(authorization, workspaceId, {
    agentCapabilities: [AGENT_CAP.FINANCE_TRANSACTION_RECORD],
  });
  await requireCommandAuthority(ctx, "finance.transaction.record", { workspaceId });
  return ctx;
}

export async function recordFinancialTransactionService(
  params: RecordFinancialTransactionParams
): Promise<FinancialTransaction> {
  await requireFinancialTransactionWrite(params.authorization, params.workspaceId);
  await getWorkspaceRecord(params.workspaceId);

  return await db.transaction(async (tx) => {
    // F07: Kiểm tra kỳ kế toán mở trước khi ghi sổ
    await assertOpenPostingPeriod(tx, {
      workspaceId: params.workspaceId,
      legalEntityId: params.legalEntityId,
      postingDate: params.transactionDate,
    });

    if (params.idempotencyKey) {
      const [existing] = await tx
        .select()
        .from(financialTransactions)
        .where(
          and(
            eq(financialTransactions.workspaceId, BigInt(params.workspaceId)),
            eq(financialTransactions.idempotencyKey, params.idempotencyKey)
          )
        )
        .limit(1);

      if (existing) {
        return toFinancialTransaction(existing);
      }
    }

    const initialStatus: ApprovalStatus = requiresApproval(params.direction, params.amount)
      ? "PENDING_APPROVAL"
      : "AUTO_APPROVED";

    if (params.projectId) {
      await assertProjectInWorkspace(params.workspaceId, params.projectId);
    }

    const [row] = await tx
      .insert(financialTransactions)
      .values({
        id: generateSnowflake(),
        workspaceId: BigInt(params.workspaceId),
        legalEntityId: params.legalEntityId ? BigInt(params.legalEntityId) : null,
        projectId: params.projectId ? BigInt(params.projectId) : null,
        transactionDate: params.transactionDate,
        description: params.description,
        amount: params.amount,
        currency: (params.currency || "VND").toUpperCase(),
        direction: params.direction,
        category: params.category || null,
        workItemId: params.workItemId ? BigInt(params.workItemId) : null,
        idempotencyKey: params.idempotencyKey || null,
        approvalStatus: initialStatus,
      })
      .returning();

    if (!row) throw APIError.internal("failed to record financial transaction");
    return toFinancialTransaction(row);
  });
}

export async function approveFinancialTransactionService(
  params: ApproveFinancialTransactionParams
): Promise<FinancialTransaction> {
  if (!params.ctx.permissions.includes("*")) {
    throw APIError.permissionDenied(
      "chỉ founder/co-founder mới có quyền duyệt giao dịch tài chính vượt ngưỡng"
    );
  }

  const [row] = await db
    .select()
    .from(financialTransactions)
    .where(
      and(
        eq(financialTransactions.id, BigInt(params.id)),
        eq(financialTransactions.workspaceId, BigInt(params.ctx.workspaceId))
      )
    )
    .limit(1);

  if (!row) throw APIError.notFound(`financial transaction ${params.id} not found`);

  if (row.approvalStatus !== "PENDING_APPROVAL") {
    throw APIError.failedPrecondition(
      `giao dịch đang ở trạng thái ${row.approvalStatus}, không thể duyệt`
    );
  }

  const [updated] = await db
    .update(financialTransactions)
    .set({
      approvalStatus: "APPROVED",
      approvedByUserId: BigInt(params.ctx.userId),
      approvedAt: new Date(),
      updatedAt: new Date(),
    })
    .where(
      and(
        eq(financialTransactions.id, BigInt(params.id)),
        eq(financialTransactions.workspaceId, BigInt(params.ctx.workspaceId))
      )
    )
    .returning();

  if (!updated) throw APIError.internal("failed to approve financial transaction");
  return toFinancialTransaction(updated);
}

export async function getFinancialTransactionService(
  id: string,
  ctx: TenantContext
): Promise<FinancialTransaction> {
  const [row] = await db
    .select()
    .from(financialTransactions)
    .where(
      and(
        eq(financialTransactions.id, BigInt(id)),
        eq(financialTransactions.workspaceId, BigInt(ctx.workspaceId))
      )
    )
    .limit(1);

  if (!row) throw APIError.notFound(`financial transaction ${id} not found`);
  return toFinancialTransaction(row);
}

export async function listFinancialTransactionsService(
  workspaceId: string,
  authorization: string | undefined,
  projectId?: string
): Promise<FinancialTransaction[]> {
  await requireWorkspaceAccess(authorization, workspaceId);

  const conditions = [eq(financialTransactions.workspaceId, BigInt(workspaceId))];
  if (projectId) {
    conditions.push(eq(financialTransactions.projectId, BigInt(projectId)));
  }

  const rows = await db
    .select()
    .from(financialTransactions)
    .where(and(...conditions))
    .orderBy(desc(financialTransactions.transactionDate));

  return rows.map(toFinancialTransaction);
}

