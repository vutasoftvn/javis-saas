import { api, Header } from "encore.dev/api";
import {
  FinancialTransaction,
  RecordFinancialTransactionParams as BaseRecordParams,
  recordFinancialTransactionService,
  approveFinancialTransactionService,
  getFinancialTransactionService,
  listFinancialTransactionsService,
} from "../services/financial-transaction.service";

export { FinancialTransaction };

export interface RecordFinancialTransactionParams extends Omit<BaseRecordParams, "authorization"> {
  authorization?: Header<"Authorization">;
}

export interface ApproveFinancialTransactionParams {
  id: number;
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
  async (params: ApproveFinancialTransactionParams): Promise<FinancialTransaction> => {
    return approveFinancialTransactionService(params);
  }
);

export const getFinancialTransaction = api(
  { method: "GET", path: "/finance-legal/transactions/:id", expose: true },
  async ({ id, authorization }: { id: number; authorization?: Header<"Authorization"> }): Promise<FinancialTransaction> => {
    return getFinancialTransactionService(id, authorization);
  }
);

export const listFinancialTransactions = api(
  { method: "GET", path: "/finance-legal/transactions", expose: true },
  async ({
    workspaceId,
    authorization,
  }: {
    workspaceId: number;
    authorization?: Header<"Authorization">;
  }): Promise<{ transactions: FinancialTransaction[] }> => {
    const transactions = await listFinancialTransactionsService(workspaceId, authorization);
    return { transactions };
  }
);
