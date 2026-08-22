import { api, APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";

const { financeExceptions } = schema;

export interface FinanceException {
  id: number;
  workspaceId: number;
  transactionId: number | null;
  exceptionType: string;
  severity: string;
  details: Record<string, unknown> | null;
  status: string;
  createdAt: string;
}

export interface RaiseFinanceExceptionParams {
  workspaceId: number;
  exceptionType: string;
  transactionId?: number;
  severity?: string;
  details?: Record<string, unknown>;
}

export const raiseFinanceException = api(
  { method: "POST", path: "/finance-legal/exceptions", expose: true },
  async (params: RaiseFinanceExceptionParams): Promise<FinanceException> => {
    await getWorkspace({ id: params.workspaceId });

    const [row] = await db
      .insert(financeExceptions)
      .values({
        workspaceId: BigInt(params.workspaceId),
        transactionId: params.transactionId ? BigInt(params.transactionId) : null,
        exceptionType: params.exceptionType,
        severity: params.severity || "WARNING",
        details: params.details || null,
      })
      .returning();

    if (!row) throw APIError.internal("failed to raise finance exception");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      transactionId: row.transactionId ? Number(row.transactionId) : null,
      exceptionType: row.exceptionType,
      severity: row.severity,
      details: row.details as Record<string, unknown> | null,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const getFinanceException = api(
  { method: "GET", path: "/finance-legal/exceptions/:id", expose: true },
  async ({ id }: { id: number }): Promise<FinanceException> => {
    const [row] = await db
      .select()
      .from(financeExceptions)
      .where(eq(financeExceptions.id, BigInt(id)))
      .limit(1);

    if (!row) throw APIError.notFound(`finance exception ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      transactionId: row.transactionId ? Number(row.transactionId) : null,
      exceptionType: row.exceptionType,
      severity: row.severity,
      details: row.details as Record<string, unknown> | null,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const resolveFinanceException = api(
  { method: "POST", path: "/finance-legal/exceptions/:id/resolve", expose: true },
  async ({ id }: { id: number }): Promise<FinanceException> => {
    const [row] = await db
      .update(financeExceptions)
      .set({ status: "RESOLVED" })
      .where(eq(financeExceptions.id, BigInt(id)))
      .returning();

    if (!row) throw APIError.notFound(`finance exception ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      transactionId: row.transactionId ? Number(row.transactionId) : null,
      exceptionType: row.exceptionType,
      severity: row.severity,
      details: row.details as Record<string, unknown> | null,
      status: row.status,
      createdAt: row.createdAt.toISOString(),
    };
  }
);
