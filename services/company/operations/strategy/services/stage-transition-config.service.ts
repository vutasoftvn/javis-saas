import { APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { assertLifecyclePrivileged } from "./lifecycle-authorization.service";

const { stageTransitionPolicies } = schema;

export interface StageTransition {
  id: string;
  workspaceId: string;
  fromStage: string;
  toStage: string;
  policyId: string | null;
  allowed: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CreateStageTransitionInput {
  fromStage: string;
  toStage: string;
  policyId?: string | number;
  allowed?: boolean;
}

export function toStageTransition(row: typeof stageTransitionPolicies.$inferSelect): StageTransition {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    fromStage: row.fromStage,
    toStage: row.toStage,
    policyId: row.policyId ? row.policyId.toString() : null,
    allowed: row.allowed,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createStageTransitionInWorkspace(
  ctx: TenantContext,
  params: CreateStageTransitionInput
): Promise<StageTransition> {
  if (!params.fromStage || !params.toStage) {
    throw APIError.invalidArgument("fromStage and toStage are required");
  }
  assertLifecyclePrivileged(ctx.membershipRole, "createStageTransition");
  const wsId = BigInt(ctx.workspaceId);

  const [row] = await db
    .insert(stageTransitionPolicies)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      fromStage: params.fromStage,
      toStage: params.toStage,
      policyId: params.policyId ? BigInt(params.policyId) : null,
      allowed: params.allowed ?? true,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create stage transition");
  return toStageTransition(row);
}

export async function getStageTransitionInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<StageTransition> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .select()
    .from(stageTransitionPolicies)
    .where(and(eq(stageTransitionPolicies.id, BigInt(id)), eq(stageTransitionPolicies.workspaceId, wsId), isNull(stageTransitionPolicies.deletedAt)))
    .limit(1);

  if (!row) throw APIError.notFound("Stage transition not found");
  return toStageTransition(row);
}

export async function listStageTransitionsInWorkspace(
  ctx: TenantContext
): Promise<{ items: StageTransition[] }> {
  const wsId = BigInt(ctx.workspaceId);

  const rows = await db
    .select()
    .from(stageTransitionPolicies)
    .where(and(eq(stageTransitionPolicies.workspaceId, wsId), isNull(stageTransitionPolicies.deletedAt)));

  return {
    items: rows.map(toStageTransition),
  };
}

export async function deleteStageTransitionInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<{ success: boolean }> {
  assertLifecyclePrivileged(ctx.membershipRole, "deleteStageTransition");
  const wsId = BigInt(ctx.workspaceId);

  const [row] = await db
    .update(stageTransitionPolicies)
    .set({ deletedAt: new Date(), updatedAt: new Date() })
    .where(and(eq(stageTransitionPolicies.id, BigInt(id)), eq(stageTransitionPolicies.workspaceId, wsId), isNull(stageTransitionPolicies.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Stage transition not found");
  return { success: true };
}
