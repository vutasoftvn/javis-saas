import { api, APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";

const { accountingFiscalProfiles, accountingCoaMappings } = schema;

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

    const [row] = await db
      .insert(accountingFiscalProfiles)
      .values({
        workspaceId: BigInt(req.workspaceId),
        fiscalYear: req.fiscalYear,
        regulationCode: req.regulationCode || "TT58_2026",
        mode: req.mode || "TT58_MODE_1",
      })
      .returning();

    if (!row) throw APIError.internal("Failed to create fiscal profile");
    return {
      id: Number(row.id),
      workspaceId: Number(row.workspaceId),
      fiscalYear: row.fiscalYear,
      regulationCode: row.regulationCode,
      mode: row.mode,
      status: row.status,
      lockedAt: row.lockedAt ? row.lockedAt.toISOString() : null,
      createdAt: row.createdAt.toISOString(),
    };
  }
);

export const listFiscalProfiles = api(
  { expose: true, method: "GET", path: "/finance-legal/workspaces/:workspaceId/fiscal-profiles" },
  async (params: { workspaceId: number }): Promise<{ profiles: AccountingFiscalProfile[] }> => {
    const rows = await db
      .select()
      .from(accountingFiscalProfiles)
      .where(eq(accountingFiscalProfiles.workspaceId, BigInt(params.workspaceId)))
      .orderBy(desc(accountingFiscalProfiles.fiscalYear));

    return {
      profiles: rows.map((row) => ({
        id: Number(row.id),
        workspaceId: Number(row.workspaceId),
        fiscalYear: row.fiscalYear,
        regulationCode: row.regulationCode,
        mode: row.mode,
        status: row.status,
        lockedAt: row.lockedAt ? row.lockedAt.toISOString() : null,
        createdAt: row.createdAt.toISOString(),
      })),
    };
  }
);

// ─── COA Mapping Endpoints ───

export const createCoaMapping = api(
  { expose: true, method: "POST", path: "/finance-legal/coa-mappings" },
  async (req: CreateCoaMappingRequest): Promise<AccountingCoaMapping> => {
    if (!req.sourceRegulation || !req.targetRegulation || !req.sourceAccountCode || !req.targetAccountCode) {
      throw APIError.invalidArgument("sourceRegulation, targetRegulation, sourceAccountCode, and targetAccountCode are required");
    }

    const [row] = await db
      .insert(accountingCoaMappings)
      .values({
        sourceRegulation: req.sourceRegulation,
        targetRegulation: req.targetRegulation,
        sourceAccountCode: req.sourceAccountCode,
        targetAccountCode: req.targetAccountCode,
        mappingType: req.mappingType || "DIRECT_1_1",
        description: req.description || null,
      })
      .returning();

    if (!row) throw APIError.internal("Failed to create COA mapping");
    return {
      id: Number(row.id),
      sourceRegulation: row.sourceRegulation,
      targetRegulation: row.targetRegulation,
      sourceAccountCode: row.sourceAccountCode,
      targetAccountCode: row.targetAccountCode,
      mappingType: row.mappingType,
      description: row.description,
    };
  }
);
