import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

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

interface AccountingPeriodRow {
  id: number;
  workspace_id: number;
  start_date: Date | string;
  end_date: Date | string;
  status: string;
  closed_by: number | null;
  closed_at: Date | string | null;
}

function formatDate(val: Date | string): string {
  if (val instanceof Date) {
    return val.toISOString().slice(0, 10);
  }
  return String(val);
}

function rowToPeriod(row: AccountingPeriodRow): AccountingPeriod {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    startDate: formatDate(row.start_date),
    endDate: formatDate(row.end_date),
    status: row.status,
    closedBy: row.closed_by,
    closedAt: row.closed_at ? (row.closed_at instanceof Date ? row.closed_at.toISOString() : String(row.closed_at)) : null,
  };
}

export const openAccountingPeriod = api(
  { method: "POST", path: "/finance-legal/accounting-periods", expose: true },
  async (params: OpenAccountingPeriodParams): Promise<AccountingPeriod> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<AccountingPeriodRow>`
      INSERT INTO finance.accounting_periods (workspace_id, start_date, end_date)
      VALUES (${params.workspaceId}, ${params.startDate}, ${params.endDate})
      RETURNING id, workspace_id, start_date, end_date, status, closed_by, closed_at
    `;
    if (!row) throw APIError.internal("failed to open accounting period");
    return rowToPeriod(row);
  }
);

export const getAccountingPeriod = api(
  { method: "GET", path: "/finance-legal/accounting-periods/:id", expose: true },
  async ({ id }: { id: number }): Promise<AccountingPeriod> => {
    const row = await financeLegalDB.queryRow<AccountingPeriodRow>`
      SELECT id, workspace_id, start_date, end_date, status, closed_by, closed_at
      FROM finance.accounting_periods WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`accounting period ${id} not found`);
    return rowToPeriod(row);
  }
);

export const closeAccountingPeriod = api(
  { method: "POST", path: "/finance-legal/accounting-periods/:id/close", expose: true },
  async ({ id }: { id: number }): Promise<AccountingPeriod> => {
    const row = await financeLegalDB.queryRow<AccountingPeriodRow>`
      UPDATE finance.accounting_periods SET status = 'CLOSED', closed_at = now()
      WHERE id = ${id}
      RETURNING id, workspace_id, start_date, end_date, status, closed_by, closed_at
    `;
    if (!row) throw APIError.notFound(`accounting period ${id} not found`);
    return rowToPeriod(row);
  }
);
