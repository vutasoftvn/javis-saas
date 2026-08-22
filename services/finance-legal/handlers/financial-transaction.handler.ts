import { api, APIError } from "encore.dev/api";
import { eq, desc, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";

const { financialTransactions } = schema;

export interface FinancialTransaction {
  id: number;
  workspaceId: number;
  documentId: number | null;
  projectId: number | null;
  cycleId: number | null;
  workItemId: number | null;
  idempotencyKey: string | null;
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
  idempotencyKey?: string;
}

export const recordFinancialTransaction = api(
  { method: "POST", path: "/finance-legal/transactions", expose: true },
  async (params: RecordFinancialTransactionParams): Promise<FinancialTransaction> => {
    await getWorkspace({ id: params.workspaceId });

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
        return {
          id: Number(existing.id),
          workspaceId: Number(existing.workspaceId),
          documentId: existing.documentId ? Number(existing.documentId) : null,
          projectId: existing.projectId ? Number(existing.projectId) : null,
          cycleId: existing.cycleId ? Number(existing.cycleId) : null,
          workItemId: existing.workItemId ? Number(existing.workItemId) : null,
          idempotencyKey: existing.idempotencyKey,
          transactionDate: String(existing.transactionDate),
          description: existing.description,
          amount: existing.amount,
          direction: existing.direction as "IN" | "OUT",
          category: existing.category,
          createdAt: existing.createdAt.toISOString(),
        };
      }
    }

    const [row] = await db
      .insert(financialTransactions)
      .values({
        workspaceId: BigInt(params.workspaceId),
        workItemId: params.workItemId ? BigInt(params.workItemId) : null,
        idempotencyKey: params.idempotencyKey || null,
        transactionDate: params.transactionDate,
        description: params.description,
        amount: params.amount,
        direction: params.direction,
        category: params.category || null,
      })
      .returning();

    if (!row) throw APIError.internal("failed to record financial transaction");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      documentId: row.documentId ? Number(row.documentId) : null,
      projectId: row.projectId ? Number(row.projectId) : null,
      cycleId: row.cycleId ? Number(row.cycleId) : null,
      workItemId: row.workItemId ? Number(row.workItemId) : null,
      idempotencyKey: row.idempotencyKey,
      transactionDate: String(row.transactionDate),
      description: row.description,
      amount: row.amount,
      direction: row.direction as "IN" | "OUT",
      category: row.category,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const getFinancialTransaction = api(
  { method: "GET", path: "/finance-legal/transactions/:id", expose: true },
  async ({ id }: { id: number }): Promise<FinancialTransaction> => {
    const [row] = await db
      .select()
      .from(financialTransactions)
      .where(eq(financialTransactions.id, BigInt(id)))
      .limit(1);

    if (!row) throw APIError.notFound(`financial transaction ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      documentId: row.documentId ? Number(row.documentId) : null,
      projectId: row.projectId ? Number(row.projectId) : null,
      cycleId: row.cycleId ? Number(row.cycleId) : null,
      workItemId: row.workItemId ? Number(row.workItemId) : null,
      idempotencyKey: row.idempotencyKey,
      transactionDate: String(row.transactionDate),
      description: row.description,
      amount: row.amount,
      direction: row.direction as "IN" | "OUT",
      category: row.category,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const listFinancialTransactions = api(
  { method: "GET", path: "/finance-legal/transactions", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<{ transactions: FinancialTransaction[] }> => {
    const rows = await db
      .select()
      .from(financialTransactions)
      .where(eq(financialTransactions.workspaceId, BigInt(workspaceId)))
      .orderBy(desc(financialTransactions.transactionDate));

    return {
      transactions: rows.map((row) => ({
        id: Number(row.id),
        workspaceId: Number(row.workspaceId),
        documentId: row.documentId ? Number(row.documentId) : null,
        projectId: row.projectId ? Number(row.projectId) : null,
        cycleId: row.cycleId ? Number(row.cycleId) : null,
        workItemId: row.workItemId ? Number(row.workItemId) : null,
        idempotencyKey: row.idempotencyKey,
        transactionDate: String(row.transactionDate),
        description: row.description,
        amount: row.amount,
        direction: row.direction as "IN" | "OUT",
        category: row.category,
        createdAt: row.createdAt.toISOString(),
      })),
    };
  }
);
