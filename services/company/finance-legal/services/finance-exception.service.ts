import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";

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

function toFinanceException(row: typeof financeExceptions.$inferSelect): FinanceException {
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

async function getFinanceExceptionRow(id: number) {
  const [row] = await db
    .select()
    .from(financeExceptions)
    .where(eq(financeExceptions.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`finance exception ${id} not found`);
  return row;
}

export async function raiseFinanceExceptionService(
  params: RaiseFinanceExceptionParams,
  authorization: string | undefined
): Promise<FinanceException> {
  await requireWorkspaceAccess(authorization, params.workspaceId);
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
  return toFinanceException(row);
}

export async function getFinanceExceptionService(
  id: number,
  authorization: string | undefined
): Promise<FinanceException> {
  const row = await getFinanceExceptionRow(id);
  await requireWorkspaceAccess(authorization, Number(row.workspaceId));
  return toFinanceException(row);
}

export async function resolveFinanceExceptionService(
  id: number,
  authorization: string | undefined
): Promise<FinanceException> {
  const existing = await getFinanceExceptionRow(id);
  await requireWorkspaceAccess(authorization, Number(existing.workspaceId));

  const [row] = await db
    .update(financeExceptions)
    .set({ status: "RESOLVED" })
    .where(eq(financeExceptions.id, BigInt(id)))
    .returning();

  if (!row) throw APIError.notFound(`finance exception ${id} not found`);
  return toFinanceException(row);
}
