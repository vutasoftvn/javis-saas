import { api, APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";

const { accountingPeriods } = schema;

export interface AccountingPeriod {
  id: number;
  workspaceId: number;
  startDate: string;
  endDate: string;
  status: string;
  closedBy: number | null;
  closedAt: string | null;
}

export interface OpenAccountingPeriodParams {
  workspaceId: number;
  startDate: string;
  endDate: string;
}

export const openAccountingPeriod = api(
  { method: "POST", path: "/finance-legal/accounting-periods", expose: true },
  async (params: OpenAccountingPeriodParams): Promise<AccountingPeriod> => {
    await getWorkspace({ id: params.workspaceId });

    const [row] = await db
      .insert(accountingPeriods)
      .values({
        workspaceId: BigInt(params.workspaceId),
        startDate: params.startDate,
        endDate: params.endDate,
      })
      .returning();

    if (!row) throw APIError.internal("failed to open accounting period");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      startDate: String(row.startDate),
      endDate: String(row.endDate),
      status: row.status,
      closedBy: row.closedBy ? Number(row.closedBy) : null,
      closedAt: row.closedAt ? row.closedAt.toISOString() : null,
    };
  }
);

export const getAccountingPeriod = api(
  { method: "GET", path: "/finance-legal/accounting-periods/:id", expose: true },
  async ({ id }: { id: number }): Promise<AccountingPeriod> => {
    const [row] = await db
      .select()
      .from(accountingPeriods)
      .where(eq(accountingPeriods.id, BigInt(id)))
      .limit(1);

    if (!row) throw APIError.notFound(`accounting period ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      startDate: String(row.startDate),
      endDate: String(row.endDate),
      status: row.status,
      closedBy: row.closedBy ? Number(row.closedBy) : null,
      closedAt: row.closedAt ? row.closedAt.toISOString() : null,
    };
  }
);

export const closeAccountingPeriod = api(
  { method: "POST", path: "/finance-legal/accounting-periods/:id/close", expose: true },
  async ({ id }: { id: number }): Promise<AccountingPeriod> => {
    const [row] = await db
      .update(accountingPeriods)
      .set({
        status: "CLOSED",
        closedAt: new Date(),
      })
      .where(eq(accountingPeriods.id, BigInt(id)))
      .returning();

    if (!row) throw APIError.notFound(`accounting period ${id} not found`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      startDate: String(row.startDate),
      endDate: String(row.endDate),
      status: row.status,
      closedBy: row.closedBy ? Number(row.closedBy) : null,
      closedAt: row.closedAt ? row.closedAt.toISOString() : null,
    };
  }
);
