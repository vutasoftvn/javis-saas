import { APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { assertLifecyclePrivileged } from "./lifecycle-authorization.service";

const { stagePolicies } = schema;

export interface StagePolicy {
  id: string;
  workspaceId: string;
  stageKey: string;
  requirements: any[];
  minimumEvidenceScore: number;
  blockingRiskRules: any[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateStagePolicyInput {
  stageKey: string;
  requirements?: any[];
  minimumEvidenceScore?: string | number;
  blockingRiskRules?: any[];
}

export interface ListStagePoliciesInput {
  stageKey?: string;
}

export interface UpdateStagePolicyInput {
  requirements?: any[];
  minimumEvidenceScore?: string | number;
  blockingRiskRules?: any[];
}

export function toStagePolicy(row: typeof stagePolicies.$inferSelect): StagePolicy {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    stageKey: row.stageKey,
    requirements: row.requirements as any[],
    minimumEvidenceScore: row.minimumEvidenceScore,
    blockingRiskRules: row.blockingRiskRules as any[],
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createStagePolicyInWorkspace(
  ctx: TenantContext,
  params: CreateStagePolicyInput
): Promise<StagePolicy> {
  if (!params.stageKey) {
    throw APIError.invalidArgument("stageKey is required");
  }
  assertLifecyclePrivileged(ctx.membershipRole, "createStagePolicy");
  const wsId = BigInt(ctx.workspaceId);

  const [row] = await db
    .insert(stagePolicies)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      stageKey: params.stageKey,
      requirements: params.requirements ?? [],
      minimumEvidenceScore:
        typeof params.minimumEvidenceScore === "string"
          ? parseFloat(params.minimumEvidenceScore)
          : (params.minimumEvidenceScore ?? 0.0),
      blockingRiskRules: params.blockingRiskRules ?? [],
    })
    .returning();

  if (!row) throw APIError.internal("failed to create stage policy");
  return toStagePolicy(row);
}

export async function getStagePolicyInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<StagePolicy> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .select()
    .from(stagePolicies)
    .where(and(eq(stagePolicies.id, BigInt(id)), eq(stagePolicies.workspaceId, wsId), isNull(stagePolicies.deletedAt)))
    .limit(1);

  if (!row) throw APIError.notFound("Stage policy not found");
  return toStagePolicy(row);
}

export async function listStagePoliciesInWorkspace(
  ctx: TenantContext,
  params: ListStagePoliciesInput
): Promise<{ items: StagePolicy[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const conditions = [eq(stagePolicies.workspaceId, wsId), isNull(stagePolicies.deletedAt)];

  if (params.stageKey) {
    conditions.push(eq(stagePolicies.stageKey, params.stageKey));
  }

  const rows = await db
    .select()
    .from(stagePolicies)
    .where(and(...conditions));

  return {
    items: rows.map(toStagePolicy),
  };
}

export async function updateStagePolicyInWorkspace(
  ctx: TenantContext,
  id: string | number,
  params: UpdateStagePolicyInput
): Promise<StagePolicy> {
  assertLifecyclePrivileged(ctx.membershipRole, "updateStagePolicy");
  const wsId = BigInt(ctx.workspaceId);

  const updateValues: Record<string, any> = { updatedAt: new Date() };
  if (params.requirements !== undefined) updateValues.requirements = params.requirements;
  if (params.minimumEvidenceScore !== undefined) {
    updateValues.minimumEvidenceScore =
      typeof params.minimumEvidenceScore === "string"
        ? parseFloat(params.minimumEvidenceScore)
        : params.minimumEvidenceScore;
  }
  if (params.blockingRiskRules !== undefined) updateValues.blockingRiskRules = params.blockingRiskRules;

  const [row] = await db
    .update(stagePolicies)
    .set(updateValues)
    .where(and(eq(stagePolicies.id, BigInt(id)), eq(stagePolicies.workspaceId, wsId), isNull(stagePolicies.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Stage policy not found");
  return toStagePolicy(row);
}

export async function deleteStagePolicyInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<{ success: boolean }> {
  assertLifecyclePrivileged(ctx.membershipRole, "deleteStagePolicy");
  const wsId = BigInt(ctx.workspaceId);

  const [row] = await db
    .update(stagePolicies)
    .set({ deletedAt: new Date(), updatedAt: new Date() })
    .where(and(eq(stagePolicies.id, BigInt(id)), eq(stagePolicies.workspaceId, wsId), isNull(stagePolicies.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Stage policy not found");
  return { success: true };
}
