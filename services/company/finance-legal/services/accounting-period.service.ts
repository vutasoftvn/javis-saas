import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { accountingPeriods } = schema;

export interface AccountingPeriod {
  id: string;
  workspaceId: string;
  startDate: string;
  endDate: string;
  status: string;
  closedBy: string | null;
  closedAt: string | null;
}

export interface OpenAccountingPeriodParams {
  workspaceId: string;
  startDate: string;
  endDate: string;
}

function toAccountingPeriod(row: typeof accountingPeriods.$inferSelect): AccountingPeriod {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    startDate: String(row.startDate),
    endDate: String(row.endDate),
    status: row.status,
    closedBy: row.closedBy ? String(row.closedBy) : null,
    closedAt: row.closedAt ? row.closedAt.toISOString() : null,
  };
}

async function getAccountingPeriodRow(id: string) {
  const [row] = await db
    .select()
    .from(accountingPeriods)
    .where(eq(accountingPeriods.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`accounting period ${id} not found`);
  return row;
}

export async function openAccountingPeriodService(
  params: OpenAccountingPeriodParams,
  authorization: string | undefined
): Promise<AccountingPeriod> {
  await requireWorkspaceAccess(authorization, params.workspaceId);
  await getWorkspace({ id: params.workspaceId });

  const [row] = await db
    .insert(accountingPeriods)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      startDate: params.startDate,
      endDate: params.endDate,
    })
    .returning();

  if (!row) throw APIError.internal("failed to open accounting period");
  return toAccountingPeriod(row);
}

export async function getAccountingPeriodService(
  id: string,
  authorization: string | undefined
): Promise<AccountingPeriod> {
  const row = await getAccountingPeriodRow(id);
  await requireWorkspaceAccess(authorization, String(row.workspaceId));
  return toAccountingPeriod(row);
}

export async function closeAccountingPeriodService(
  id: string,
  authorization: string | undefined
): Promise<AccountingPeriod> {
  const existing = await getAccountingPeriodRow(id);
  await requireWorkspaceAccess(authorization, String(existing.workspaceId));

  const [row] = await db
    .update(accountingPeriods)
    .set({
      status: "CLOSED",
      closedAt: new Date(),
    })
    .where(eq(accountingPeriods.id, BigInt(id)))
    .returning();

  if (!row) throw APIError.notFound(`accounting period ${id} not found`);
  return toAccountingPeriod(row);
}
