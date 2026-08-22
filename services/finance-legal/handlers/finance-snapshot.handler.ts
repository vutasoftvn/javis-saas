import { api, APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";

const { financeManagementSnapshots } = schema;

export interface FinanceManagementSnapshot {
  id: number;
  workspaceId: number;
  cycleId: number | null;
  asOf: string;
  cash: string;
  burn: string;
  runwayMonths: string | null;
  revenue: string;
  expenses: string;
  budgetVariance: string | null;
  createdAt: string;
}

export interface RecordFinanceSnapshotParams {
  workspaceId: number;
  asOf: string;
  cash: string;
  burn: string;
  revenue?: string;
  expenses?: string;
}

export const recordFinanceSnapshot = api(
  { method: "POST", path: "/finance-legal/snapshots", expose: true },
  async (params: RecordFinanceSnapshotParams): Promise<FinanceManagementSnapshot> => {
    await getWorkspace({ id: params.workspaceId });

    const [row] = await db
      .insert(financeManagementSnapshots)
      .values({
        workspaceId: BigInt(params.workspaceId),
        asOf: params.asOf,
        cash: params.cash,
        burn: params.burn,
        revenue: params.revenue || "0",
        expenses: params.expenses || "0",
      })
      .returning();

    if (!row) throw APIError.internal("failed to record finance snapshot");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      cycleId: row.cycleId ? Number(row.cycleId) : null,
      asOf: String(row.asOf),
      cash: row.cash,
      burn: row.burn,
      runwayMonths: row.runwayMonths,
      revenue: row.revenue,
      expenses: row.expenses,
      budgetVariance: row.budgetVariance,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const getLatestFinanceSnapshot = api(
  { method: "GET", path: "/finance-legal/snapshots/latest", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<FinanceManagementSnapshot> => {
    const [row] = await db
      .select()
      .from(financeManagementSnapshots)
      .where(eq(financeManagementSnapshots.workspaceId, BigInt(workspaceId)))
      .orderBy(desc(financeManagementSnapshots.asOf))
      .limit(1);

    if (!row) throw APIError.notFound(`no finance snapshot for workspace ${workspaceId}`);
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      cycleId: row.cycleId ? Number(row.cycleId) : null,
      asOf: String(row.asOf),
      cash: row.cash,
      burn: row.burn,
      runwayMonths: row.runwayMonths,
      revenue: row.revenue,
      expenses: row.expenses,
      budgetVariance: row.budgetVariance,
      createdAt: row.createdAt.toISOString(),
    };
  }
);
