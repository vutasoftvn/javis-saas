import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { financeExceptions } = schema;

export interface FinanceException {
  id: string;
  workspaceId: string;
  transactionId: string | null;
  exceptionType: string;
  severity: string;
  details: Record<string, unknown> | null;
  status: string;
  createdAt: string;
}

export interface RaiseFinanceExceptionParams {
  workspaceId: string;
  exceptionType: string;
  transactionId?: string;
  severity?: string;
  details?: Record<string, unknown>;
}

function toFinanceException(row: typeof financeExceptions.$inferSelect): FinanceException {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    transactionId: row.transactionId ? String(row.transactionId) : null,
    exceptionType: row.exceptionType,
    severity: row.severity,
    details: row.details as Record<string, unknown> | null,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
  };
}

async function getFinanceExceptionRow(id: string) {
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
  await getWorkspace({ id: String(params.workspaceId) });

  const [row] = await db
    .insert(financeExceptions)
    .values({
      id: generateSnowflake(),
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
  id: string,
  authorization: string | undefined
): Promise<FinanceException> {
  const row = await getFinanceExceptionRow(id);
  await requireWorkspaceAccess(authorization, String(row.workspaceId));
  return toFinanceException(row);
}

export async function resolveFinanceExceptionService(
  id: string,
  authorization: string | undefined
): Promise<FinanceException> {
  const existing = await getFinanceExceptionRow(id);
  await requireWorkspaceAccess(authorization, String(existing.workspaceId));

  const [row] = await db
    .update(financeExceptions)
    .set({ status: "RESOLVED" })
    .where(eq(financeExceptions.id, BigInt(id)))
    .returning();

  if (!row) throw APIError.notFound(`finance exception ${id} not found`);
  return toFinanceException(row);
}
