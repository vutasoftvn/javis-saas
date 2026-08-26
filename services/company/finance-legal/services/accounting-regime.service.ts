import { APIError } from "encore.dev/api";
import { eq, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { accountingFiscalProfiles, accountingCoaMappings } = schema;

export interface AccountingFiscalProfile {
  id: string;
  workspaceId: string;
  fiscalYear: number;
  regulationCode: string;
  mode: string;
  status: string;
  lockedAt?: string | null;
  createdAt: string;
}

export interface CreateFiscalProfileRequest {
  workspaceId: string;
  fiscalYear: number;
  regulationCode?: string;
  mode?: string;
}

export interface AccountingCoaMapping {
  id: string;
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

function toFiscalProfile(row: typeof accountingFiscalProfiles.$inferSelect): AccountingFiscalProfile {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    fiscalYear: row.fiscalYear,
    regulationCode: row.regulationCode,
    mode: row.mode,
    status: row.status,
    lockedAt: row.lockedAt ? row.lockedAt.toISOString() : null,
    createdAt: row.createdAt.toISOString(),
  };
}

export async function createFiscalProfileService(
  req: CreateFiscalProfileRequest,
  authorization: string | undefined
): Promise<AccountingFiscalProfile> {
  if (!req.workspaceId || !req.fiscalYear) {
    throw APIError.invalidArgument("workspaceId and fiscalYear are required");
  }
  await requireWorkspaceAccess(authorization, req.workspaceId);

  const [row] = await db
    .insert(accountingFiscalProfiles)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(req.workspaceId),
      fiscalYear: req.fiscalYear,
      regulationCode: req.regulationCode || "TT58_2026",
      mode: req.mode || "TT58_MODE_1",
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create fiscal profile");
  return toFiscalProfile(row);
}

export async function listFiscalProfilesService(
  workspaceId: string | number,
  authorization: string | undefined
): Promise<AccountingFiscalProfile[]> {
  await requireWorkspaceAccess(authorization, workspaceId);

  const rows = await db
    .select()
    .from(accountingFiscalProfiles)
    .where(eq(accountingFiscalProfiles.workspaceId, BigInt(workspaceId)))
    .orderBy(desc(accountingFiscalProfiles.fiscalYear));

  return rows.map(toFiscalProfile);
}

export async function createCoaMappingService(req: CreateCoaMappingRequest): Promise<AccountingCoaMapping> {
  if (!req.sourceRegulation || !req.targetRegulation || !req.sourceAccountCode || !req.targetAccountCode) {
    throw APIError.invalidArgument("sourceRegulation, targetRegulation, sourceAccountCode, and targetAccountCode are required");
  }

  const [row] = await db
    .insert(accountingCoaMappings)
    .values({
      id: generateSnowflake(),
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
    id: String(row.id),
    sourceRegulation: row.sourceRegulation,
    targetRegulation: row.targetRegulation,
    sourceAccountCode: row.sourceAccountCode,
    targetAccountCode: row.targetAccountCode,
    mappingType: row.mappingType,
    description: row.description,
  };
}
