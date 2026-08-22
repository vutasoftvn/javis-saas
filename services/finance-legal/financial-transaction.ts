import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface FinancialTransaction {
  id: number;
  workspaceId: number;
  documentId: number | null;
  projectId: number | null;
  cycleId: number | null;
  workItemId: number | null;
  transactionDate: string;
  description: string;
  amount: string;
  direction: "IN" | "OUT";
  category: string | null;
  createdAt: string;
}

export interface RecordFinancialTransactionParams {
  workspaceId: number;
  transactionDate: string;
  description: string;
  amount: string;
  direction: "IN" | "OUT";
  category?: string;
  workItemId?: number;
}

interface FinancialTransactionRow {
  id: number;
  workspace_id: number;
  document_id: number | null;
  project_id: number | null;
  cycle_id: number | null;
  work_item_id: number | null;
  transaction_date: Date | string;
  description: string;
  amount: string;
  direction: string;
  category: string | null;
  created_at: Date | string;
}

const TRANSACTION_COLUMNS = `id, workspace_id, document_id, project_id, cycle_id, work_item_id,
  transaction_date, description, amount, direction, category, created_at`;

function formatDate(val: Date | string): string {
  if (val instanceof Date) {
    return val.toISOString().slice(0, 10);
  }
  return String(val);
}

function formatTimestamp(val: Date | string): string {
  if (val instanceof Date) {
    return val.toISOString();
  }
  return String(val);
}

function rowToTransaction(row: FinancialTransactionRow): FinancialTransaction {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    documentId: row.document_id,
    projectId: row.project_id,
    cycleId: row.cycle_id,
    workItemId: row.work_item_id,
    transactionDate: formatDate(row.transaction_date),
    description: row.description,
    amount: row.amount,
    direction: row.direction as "IN" | "OUT",
    category: row.category,
    createdAt: formatTimestamp(row.created_at),
  };
}

export const recordFinancialTransaction = api(
  { method: "POST", path: "/finance-legal/transactions", expose: true },
  async (params: RecordFinancialTransactionParams): Promise<FinancialTransaction> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<FinancialTransactionRow>`
      INSERT INTO finance.financial_transactions (workspace_id, work_item_id, transaction_date, description, amount, direction, category)
      VALUES (
        ${params.workspaceId}, ${params.workItemId ?? null}, ${params.transactionDate}, ${params.description},
        ${params.amount}, ${params.direction}, ${params.category ?? null}
      )
      RETURNING id, workspace_id, document_id, project_id, cycle_id, work_item_id, transaction_date, description, amount::text as amount, direction, category, created_at
    `;
    if (!row) throw APIError.internal("failed to record financial transaction");
    return rowToTransaction(row);
  }
);

export const getFinancialTransaction = api(
  { method: "GET", path: "/finance-legal/transactions/:id", expose: true },
  async ({ id }: { id: number }): Promise<FinancialTransaction> => {
    const row = await financeLegalDB.queryRow<FinancialTransactionRow>`
      SELECT id, workspace_id, document_id, project_id, cycle_id, work_item_id, transaction_date, description, amount::text as amount, direction, category, created_at
      FROM finance.financial_transactions WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`financial transaction ${id} not found`);
    return rowToTransaction(row);
  }
);

export const listFinancialTransactions = api(
  { method: "GET", path: "/finance-legal/transactions", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<{ transactions: FinancialTransaction[] }> => {
    const rows = financeLegalDB.query<FinancialTransactionRow>`
      SELECT id, workspace_id, document_id, project_id, cycle_id, work_item_id, transaction_date, description, amount::text as amount, direction, category, created_at
      FROM finance.financial_transactions WHERE workspace_id = ${workspaceId}
      ORDER BY transaction_date DESC
    `;
    const transactions: FinancialTransaction[] = [];
    for await (const row of rows) {
      transactions.push(rowToTransaction(row));
    }
    return { transactions };
  }
);
