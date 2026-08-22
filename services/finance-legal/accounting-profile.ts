import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface AccountingProfile {
  id: number;
  workspaceId: number;
  mode: string;
  status: string;
  confirmedBy: number | null;
  confirmedAt: string | null;
  createdAt: string;
}

export interface CreateAccountingProfileParams {
  workspaceId: number;
  mode?: string;
}

interface AccountingProfileRow {
  id: number;
  workspace_id: number;
  mode: string;
  status: string;
  confirmed_by: number | null;
  confirmed_at: Date | null;
  created_at: Date;
}

function rowToProfile(row: AccountingProfileRow): AccountingProfile {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    mode: row.mode,
    status: row.status,
    confirmedBy: row.confirmed_by,
    confirmedAt: row.confirmed_at ? row.confirmed_at.toISOString() : null,
    createdAt: row.created_at.toISOString(),
  };
}

export const createAccountingProfile = api(
  { method: "POST", path: "/finance-legal/accounting-profiles", expose: true },
  async (params: CreateAccountingProfileParams): Promise<AccountingProfile> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<AccountingProfileRow>`
      INSERT INTO finance.accounting_profiles (workspace_id, mode)
      VALUES (${params.workspaceId}, ${params.mode ?? "TT58_MODE_1"})
      RETURNING id, workspace_id, mode, status, confirmed_by, confirmed_at, created_at
    `;
    if (!row) throw APIError.internal("failed to create accounting profile");
    return rowToProfile(row);
  }
);

export const getAccountingProfileByWorkspace = api(
  { method: "GET", path: "/finance-legal/accounting-profiles/by-workspace/:workspaceId", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<AccountingProfile> => {
    const row = await financeLegalDB.queryRow<AccountingProfileRow>`
      SELECT id, workspace_id, mode, status, confirmed_by, confirmed_at, created_at
      FROM finance.accounting_profiles WHERE workspace_id = ${workspaceId}
    `;
    if (!row) throw APIError.notFound(`no accounting profile for workspace ${workspaceId}`);
    return rowToProfile(row);
  }
);
