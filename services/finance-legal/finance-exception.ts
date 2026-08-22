import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

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

interface FinanceExceptionRow {
  id: number;
  workspace_id: number;
  transaction_id: number | null;
  exception_type: string;
  severity: string;
  details: Record<string, unknown> | null;
  status: string;
  created_at: Date;
}

function rowToException(row: FinanceExceptionRow): FinanceException {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    transactionId: row.transaction_id,
    exceptionType: row.exception_type,
    severity: row.severity,
    details: row.details,
    status: row.status,
    createdAt: row.created_at.toISOString(),
  };
}

export const raiseFinanceException = api(
  { method: "POST", path: "/finance-legal/exceptions", expose: true },
  async (params: RaiseFinanceExceptionParams): Promise<FinanceException> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<FinanceExceptionRow>`
      INSERT INTO finance.finance_exceptions (workspace_id, transaction_id, exception_type, severity, details)
      VALUES (
        ${params.workspaceId}, ${params.transactionId ?? null}, ${params.exceptionType},
        ${params.severity ?? "WARNING"}, ${params.details ? JSON.stringify(params.details) : null}
      )
      RETURNING id, workspace_id, transaction_id, exception_type, severity, details, status, created_at
    `;
    if (!row) throw APIError.internal("failed to raise finance exception");
    return rowToException(row);
  }
);

export const getFinanceException = api(
  { method: "GET", path: "/finance-legal/exceptions/:id", expose: true },
  async ({ id }: { id: number }): Promise<FinanceException> => {
    const row = await financeLegalDB.queryRow<FinanceExceptionRow>`
      SELECT id, workspace_id, transaction_id, exception_type, severity, details, status, created_at
      FROM finance.finance_exceptions WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`finance exception ${id} not found`);
    return rowToException(row);
  }
);

export const resolveFinanceException = api(
  { method: "POST", path: "/finance-legal/exceptions/:id/resolve", expose: true },
  async ({ id }: { id: number }): Promise<FinanceException> => {
    const row = await financeLegalDB.queryRow<FinanceExceptionRow>`
      UPDATE finance.finance_exceptions SET status = 'RESOLVED'
      WHERE id = ${id}
      RETURNING id, workspace_id, transaction_id, exception_type, severity, details, status, created_at
    `;
    if (!row) throw APIError.notFound(`finance exception ${id} not found`);
    return rowToException(row);
  }
);
