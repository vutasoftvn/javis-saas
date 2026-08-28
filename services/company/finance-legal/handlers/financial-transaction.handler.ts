import { api, Header } from "encore.dev/api";
import {
  FinancialTransaction,
  RecordFinancialTransactionParams as BaseRecordParams,
  recordFinancialTransactionService,
  approveFinancialTransactionService,
  getFinancialTransactionService,
  listFinancialTransactionsService,
} from "../services/financial-transaction.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

export { FinancialTransaction };

export interface RecordFinancialTransactionParams extends Omit<BaseRecordParams, "authorization"> {
  authorization?: Header<"Authorization">;
}

export interface ApproveFinancialTransactionParams {
  id: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export const recordFinancialTransaction = api(
  { method: "POST", path: "/finance-legal/transactions", expose: true },
  async (params: RecordFinancialTransactionParams): Promise<FinancialTransaction> => {
    return recordFinancialTransactionService(params);
  }
);

/**
 * Duyệt một giao dịch OUT vượt ngưỡng rủi ro (approvalStatus = PENDING_APPROVAL).
 * Chỉ role founder/co-founder trong workspace của giao dịch mới được gọi.
 */
export const approveFinancialTransaction = api(
  { method: "POST", path: "/finance-legal/transactions/:id/approve", expose: true },
  async ({
    id,
    workspaceId,
    authorization,
  }: ApproveFinancialTransactionParams): Promise<FinancialTransaction> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return approveFinancialTransactionService({ id, ctx });
  }
);

export const getFinancialTransaction = api(
  { method: "GET", path: "/finance-legal/transactions/:id", expose: true },
  async ({
    id,
    workspaceId,
    authorization,
  }: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<FinancialTransaction> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getFinancialTransactionService(id, ctx);
  }
);

export const listFinancialTransactions = api(
  { method: "GET", path: "/finance-legal/transactions", expose: true },
  async ({
    workspaceId,
    authorization,
  }: {
    workspaceId: string;
    authorization?: Header<"Authorization">;
  }): Promise<{ transactions: FinancialTransaction[] }> => {
    const transactions = await listFinancialTransactionsService(workspaceId, authorization);
    return { transactions };
  }
);

