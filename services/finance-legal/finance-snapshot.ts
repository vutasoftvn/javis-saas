import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

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

interface FinanceSnapshotRow {
  id: number;
  workspace_id: number;
  cycle_id: number | null;
  as_of: Date | string;
  cash: string;
  burn: string;
  runway_months: string | null;
  revenue: string;
  expenses: string;
  budget_variance: string | null;
  created_at: Date | string;
}

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

function rowToSnapshot(row: FinanceSnapshotRow): FinanceManagementSnapshot {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    cycleId: row.cycle_id,
    asOf: formatDate(row.as_of),
    cash: row.cash,
    burn: row.burn,
    runwayMonths: row.runway_months,
    revenue: row.revenue,
    expenses: row.expenses,
    budgetVariance: row.budget_variance,
    createdAt: formatTimestamp(row.created_at),
  };
}

export const recordFinanceSnapshot = api(
  { method: "POST", path: "/finance-legal/snapshots", expose: true },
  async (params: RecordFinanceSnapshotParams): Promise<FinanceManagementSnapshot> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<FinanceSnapshotRow>`
      INSERT INTO finance.finance_management_snapshots (workspace_id, as_of, cash, burn, revenue, expenses)
      VALUES (
        ${params.workspaceId}, ${params.asOf}, ${params.cash}, ${params.burn},
        ${params.revenue ?? "0"}, ${params.expenses ?? "0"}
      )
      RETURNING id, workspace_id, cycle_id, as_of, cash::text as cash, burn::text as burn, runway_months::text as runway_months, revenue::text as revenue, expenses::text as expenses, budget_variance::text as budget_variance, created_at
    `;
    if (!row) throw APIError.internal("failed to record finance snapshot");
    return rowToSnapshot(row);
  }
);

export const getLatestFinanceSnapshot = api(
  { method: "GET", path: "/finance-legal/snapshots/latest", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<FinanceManagementSnapshot> => {
    const row = await financeLegalDB.queryRow<FinanceSnapshotRow>`
      SELECT id, workspace_id, cycle_id, as_of, cash::text as cash, burn::text as burn, runway_months::text as runway_months, revenue::text as revenue, expenses::text as expenses, budget_variance::text as budget_variance, created_at
      FROM finance.finance_management_snapshots
      WHERE workspace_id = ${workspaceId}
      ORDER BY as_of DESC LIMIT 1
    `;
    if (!row) throw APIError.notFound(`no finance snapshot for workspace ${workspaceId}`);
    return rowToSnapshot(row);
  }
);
