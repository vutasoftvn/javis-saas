import { APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getProjectInWorkspace } from "../../services/project-access.service";
import { JsonObject, toJsonObject } from "./strategy-json";

const { discoverySignals } = schema;

export interface DiscoverySignal {
  id: string;
  workspaceId: string;
  projectId: string;
  signalType: string;
  payload: JsonObject;
  source: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateDiscoverySignalInput {
  projectId: string | number;
  signalType: string;
  payload?: JsonObject;
  source: string;
}

export interface ListDiscoverySignalsInput {
  projectId?: string | number;
  signalType?: string;
}

export interface UpdateDiscoverySignalInput {
  signalType?: string;
  payload?: JsonObject;
  source?: string;
}

export function toDiscoverySignal(row: typeof discoverySignals.$inferSelect): DiscoverySignal {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    signalType: row.signalType,
    payload: toJsonObject(row.payload),
    source: row.source,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export async function createDiscoverySignalInWorkspace(
  ctx: TenantContext,
  params: CreateDiscoverySignalInput
): Promise<DiscoverySignal> {
  if (!params.projectId || !params.signalType || !params.source) {
    throw APIError.invalidArgument("projectId, signalType, and source are required");
  }
  const wsId = BigInt(ctx.workspaceId);

  // Verify project belongs to workspace
  await getProjectInWorkspace(params.projectId, ctx);

  const [row] = await db
    .insert(discoverySignals)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: BigInt(params.projectId),
      signalType: params.signalType,
      payload: params.payload ?? {},
      source: params.source,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create discovery signal");
  return toDiscoverySignal(row);
}

export async function getDiscoverySignalInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<DiscoverySignal> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .select()
    .from(discoverySignals)
    .where(and(eq(discoverySignals.id, BigInt(id)), eq(discoverySignals.workspaceId, wsId), isNull(discoverySignals.deletedAt)))
    .limit(1);

  if (!row) throw APIError.notFound("Discovery signal not found");
  return toDiscoverySignal(row);
}

export async function listDiscoverySignalsInWorkspace(
  ctx: TenantContext,
  params: ListDiscoverySignalsInput
): Promise<{ items: DiscoverySignal[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const conditions = [eq(discoverySignals.workspaceId, wsId), isNull(discoverySignals.deletedAt)];

  if (params.projectId) {
    conditions.push(eq(discoverySignals.projectId, BigInt(params.projectId)));
  }
  if (params.signalType) {
    conditions.push(eq(discoverySignals.signalType, params.signalType));
  }

  const rows = await db
    .select()
    .from(discoverySignals)
    .where(and(...conditions));

  return {
    items: rows.map(toDiscoverySignal),
  };
}

export async function updateDiscoverySignalInWorkspace(
  ctx: TenantContext,
  id: string | number,
  params: UpdateDiscoverySignalInput
): Promise<DiscoverySignal> {
  const wsId = BigInt(ctx.workspaceId);

  const updateValues = {
    updatedAt: new Date(),
    ...(params.signalType !== undefined ? { signalType: params.signalType } : {}),
    ...(params.payload !== undefined ? { payload: params.payload } : {}),
    ...(params.source !== undefined ? { source: params.source } : {}),
  };

  const [row] = await db
    .update(discoverySignals)
    .set(updateValues)
    .where(and(eq(discoverySignals.id, BigInt(id)), eq(discoverySignals.workspaceId, wsId), isNull(discoverySignals.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Discovery signal not found");
  return toDiscoverySignal(row);
}

export async function deleteDiscoverySignalInWorkspace(
  ctx: TenantContext,
  id: string | number
): Promise<{ success: boolean }> {
  const wsId = BigInt(ctx.workspaceId);
  const [row] = await db
    .update(discoverySignals)
    .set({ deletedAt: new Date(), updatedAt: new Date() })
    .where(and(eq(discoverySignals.id, BigInt(id)), eq(discoverySignals.workspaceId, wsId), isNull(discoverySignals.deletedAt)))
    .returning();

  if (!row) throw APIError.notFound("Discovery signal not found");
  return { success: true };
}
