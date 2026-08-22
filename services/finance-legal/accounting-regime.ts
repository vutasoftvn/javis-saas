import { api, APIError } from "encore.dev/api";
import { financeLegalDB as db } from "./db";

export interface AccountingFiscalProfile {
  id: number;
  workspaceId: number;
  fiscalYear: number;
  regulationCode: string;
  mode: string;
  status: string;
  lockedAt?: string | null;
  createdAt: string;
}

export interface CreateFiscalProfileRequest {
  workspaceId: number;
  fiscalYear: number;
  regulationCode?: string;
  mode?: string;
}

export interface AccountingCoaMapping {
  id: number;
  sourceRegulation: string;
  targetRegulation: string;
  sourceAccountCode: string;
  targetAccountCode: string;
  mappingType: string;
  description?: string | null;
}

export interface CreateCoaMappingRequest {
  sourceRegulation: string;
  targetRegulation: string;
  sourceAccountCode: string;
  targetAccountCode: string;
  mappingType?: string;
  description?: string | null;
}

// ─── Fiscal Profiles Endpoints ───

export const createFiscalProfile = api(
  { expose: true, method: "POST", path: "/finance-legal/fiscal-profiles" },
  async (req: CreateFiscalProfileRequest): Promise<AccountingFiscalProfile> => {
    if (!req.workspaceId || !req.fiscalYear) {
      throw APIError.invalidArgument("workspaceId and fiscalYear are required");
    }

    const row = await db.queryRow<AccountingFiscalProfile>`
      INSERT INTO finance.accounting_fiscal_profiles (
        workspace_id, fiscal_year, regulation_code, mode
      ) VALUES (
        ${req.workspaceId}, ${req.fiscalYear},
        ${req.regulationCode ?? "TT58_2026"},
        ${req.mode ?? "TT58_MODE_1"}
      )
      RETURNING
        id, workspace_id as "workspaceId", fiscal_year as "fiscalYear",
        regulation_code as "regulationCode", mode, status,
        locked_at as "lockedAt", created_at as "createdAt"
    `;
    if (!row) throw APIError.internal("Failed to create fiscal profile");
    return row;
  }
);

export const listFiscalProfiles = api(
  { expose: true, method: "GET", path: "/finance-legal/workspaces/:workspaceId/fiscal-profiles" },
  async (params: { workspaceId: number }): Promise<{ profiles: AccountingFiscalProfile[] }> => {
    const rows = db.query<AccountingFiscalProfile>`
      SELECT
        id, workspace_id as "workspaceId", fiscal_year as "fiscalYear",
        regulation_code as "regulationCode", mode, status,
        locked_at as "lockedAt", created_at as "createdAt"
      FROM finance.accounting_fiscal_profiles
      WHERE workspace_id = ${params.workspaceId}
      ORDER BY fiscal_year DESC
    `;
    const profiles: AccountingFiscalProfile[] = [];
    for await (const row of rows) profiles.push(row);
    return { profiles };
  }
);

// ─── COA Mapping Endpoints ───

export const createCoaMapping = api(
  { expose: true, method: "POST", path: "/finance-legal/coa-mappings" },
  async (req: CreateCoaMappingRequest): Promise<AccountingCoaMapping> => {
    if (!req.sourceRegulation || !req.targetRegulation || !req.sourceAccountCode || !req.targetAccountCode) {
      throw APIError.invalidArgument("sourceRegulation, targetRegulation, sourceAccountCode, and targetAccountCode are required");
    }

    const row = await db.queryRow<AccountingCoaMapping>`
      INSERT INTO finance.accounting_coa_mappings (
        source_regulation, target_regulation, source_account_code, target_account_code,
        mapping_type, description
      ) VALUES (
        ${req.sourceRegulation}, ${req.targetRegulation},
        ${req.sourceAccountCode}, ${req.targetAccountCode},
        ${req.mappingType ?? "DIRECT_1_1"}, ${req.description ?? null}
      )
      RETURNING
        id, source_regulation as "sourceRegulation", target_regulation as "targetRegulation",
        source_account_code as "sourceAccountCode", target_account_code as "targetAccountCode",
        mapping_type as "mappingType", description
    `;
    if (!row) throw APIError.internal("Failed to create COA mapping");
    return row;
  }
);
