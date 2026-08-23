import { APIError } from "encore.dev/api";
import { eq, and, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";

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
  documentId: string | null;
  projectId: string | null;
  cycleId: string | null;
  workItemId: string | null;
  idempotencyKey: string | null;
  transactionDate: string;
  description: string;
  amount: string;
  direction: "IN" | "OUT";
  category: string | null;
  approvalStatus: ApprovalStatus;
  approvedByUserId: string | null;
  approvedAt: string | null;
  createdAt: string;
}

export interface RecordFinancialTransactionParams {
  workspaceId: string | number;
  transactionDate: string;
  description: string;
  amount: string;
  direction: "IN" | "OUT";
  category?: string;
  workItemId?: string | number;
  idempotencyKey?: string;
  authorization?: string;
}

export interface ApproveFinancialTransactionParams {
  id: string | number;
  authorization?: string;
}

function requiresApproval(direction: "IN" | "OUT", amount: string): boolean {
  if (direction !== "OUT") return false;
  return Math.abs(Number(amount)) >= FINANCIAL_TRANSACTION_APPROVAL_THRESHOLD;
}

function toFinancialTransaction(row: typeof financialTransactions.$inferSelect): FinancialTransaction {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    documentId: row.documentId ? String(row.documentId) : null,
    projectId: row.projectId ? String(row.projectId) : null,
    cycleId: row.cycleId ? String(row.cycleId) : null,
    workItemId: row.workItemId ? String(row.workItemId) : null,
    idempotencyKey: row.idempotencyKey,
    transactionDate: String(row.transactionDate),
    description: row.description,
    amount: row.amount,
    direction: row.direction as "IN" | "OUT",
    category: row.category,
    approvalStatus: row.approvalStatus as ApprovalStatus,
    approvedByUserId: row.approvedByUserId ? String(row.approvedByUserId) : null,
    approvedAt: row.approvedAt ? row.approvedAt.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function recordFinancialTransactionService(
  params: RecordFinancialTransactionParams
): Promise<FinancialTransaction> {
  await requireWorkspaceAccess(params.authorization, params.workspaceId);
  await getWorkspace({ id: String(params.workspaceId) });

  if (params.idempotencyKey) {
    const [existing] = await db
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

  const approvalStatus: ApprovalStatus = requiresApproval(params.direction, params.amount)
    ? "PENDING_APPROVAL"
    : "AUTO_APPROVED";

  const [row] = await db
    .insert(financialTransactions)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      workItemId: params.workItemId ? BigInt(params.workItemId) : null,
      idempotencyKey: params.idempotencyKey || null,
      transactionDate: params.transactionDate,
      description: params.description,
      amount: params.amount,
      direction: params.direction,
      category: params.category || null,
      approvalStatus,
    })
    .returning();

  if (!row) throw APIError.internal("failed to record financial transaction");
  return toFinancialTransaction(row);
}

export async function approveFinancialTransactionService(
  params: ApproveFinancialTransactionParams
): Promise<FinancialTransaction> {
  const [row] = await db
    .select()
    .from(financialTransactions)
    .where(eq(financialTransactions.id, BigInt(params.id)))
    .limit(1);

  if (!row) throw APIError.notFound(`financial transaction ${params.id} not found`);

  if (row.approvalStatus !== "PENDING_APPROVAL") {
    throw APIError.invalidArgument(
      `financial transaction ${params.id} không ở trạng thái chờ duyệt (hiện tại: ${row.approvalStatus})`
    );
  }

  const tenantCtx = await resolveTenantContext({
    authorization: params.authorization,
    workspaceId: row.workspaceId,
  });

  if (!tenantCtx.permissions.includes("*")) {
    throw APIError.permissionDenied(
      "chỉ founder/co-founder mới có quyền duyệt giao dịch tài chính vượt ngưỡng"
    );
  }

  const [updated] = await db
    .update(financialTransactions)
    .set({
      approvalStatus: "APPROVED",
      approvedByUserId: BigInt(tenantCtx.userId),
      approvedAt: new Date(),
      updatedAt: new Date(),
    })
    .where(eq(financialTransactions.id, BigInt(params.id)))
    .returning();

  if (!updated) throw APIError.internal("failed to approve financial transaction");
  return toFinancialTransaction(updated);
}

export async function getFinancialTransactionService(
  id: string | number,
  authorization: string | undefined
): Promise<FinancialTransaction> {
  const [row] = await db
    .select()
    .from(financialTransactions)
    .where(eq(financialTransactions.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`financial transaction ${id} not found`);
  await requireWorkspaceAccess(authorization, row.workspaceId);
  return toFinancialTransaction(row);
}

export async function listFinancialTransactionsService(
  workspaceId: string | number,
  authorization: string | undefined
): Promise<FinancialTransaction[]> {
  await requireWorkspaceAccess(authorization, workspaceId);

  const rows = await db
    .select()
    .from(financialTransactions)
    .where(eq(financialTransactions.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(financialTransactions.transactionDate));

  return rows.map(toFinancialTransaction);
}
