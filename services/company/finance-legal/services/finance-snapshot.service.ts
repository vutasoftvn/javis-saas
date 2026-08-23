import { APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { getWorkspace } from "../../identity/handlers/workspace.handler";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { financeManagementSnapshots } = schema;

export interface FinanceManagementSnapshot {
  id: string;
  workspaceId: string;
  cycleId: string | null;
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
  workspaceId: string;
  asOf: string;
  cash: string;
  burn: string;
  revenue?: string;
  expenses?: string;
}

function toFinanceSnapshot(row: typeof financeManagementSnapshots.$inferSelect): FinanceManagementSnapshot {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    cycleId: row.cycleId ? String(row.cycleId) : null,
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

export async function recordFinanceSnapshotService(
  params: RecordFinanceSnapshotParams,
  authorization: string | undefined
): Promise<FinanceManagementSnapshot> {
  await requireWorkspaceAccess(authorization, String(params.workspaceId));
  await getWorkspace({ id: String(params.workspaceId) });

  const [row] = await db
    .insert(financeManagementSnapshots)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      asOf: params.asOf,
      cash: params.cash,
      burn: params.burn,
      revenue: params.revenue || "0",
      expenses: params.expenses || "0",
    })
    .returning();

  if (!row) throw APIError.internal("failed to record finance snapshot");
  return toFinanceSnapshot(row);
}

export async function getLatestFinanceSnapshotService(
  workspaceId: string,
  authorization: string | undefined
): Promise<FinanceManagementSnapshot> {
  await requireWorkspaceAccess(authorization, String(workspaceId));

  const [row] = await db
    .select()
    .from(financeManagementSnapshots)
    .where(eq(financeManagementSnapshots.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(financeManagementSnapshots.asOf))
    .limit(1);

  if (!row) throw APIError.notFound(`no finance snapshot for workspace ${workspaceId}`);
  return toFinanceSnapshot(row);
}
