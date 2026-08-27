import { api, APIError, Header } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { getProjectInWorkspace } from "../../services/project-access.service";

const { discoverySignals } = schema;

export interface DiscoverySignal {
  id: string;
  workspaceId: string;
  projectId: string;
  signalType: string;
  payload: Record<string, any>;
  source: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateDiscoverySignalParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string | number;
  signalType: string;
  payload?: Record<string, any>;
  source: string;
}

export interface ListDiscoverySignalsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId?: string | number;
  signalType?: string;
}

export interface UpdateDiscoverySignalParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  id: string;
  signalType?: string;
  payload?: Record<string, any>;
  source?: string;
}

function toDiscoverySignal(row: typeof discoverySignals.$inferSelect): DiscoverySignal {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    signalType: row.signalType,
    payload: row.payload as Record<string, any>,
    source: row.source,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export const createDiscoverySignal = api(
  { method: "POST", path: "/operations/strategy/discovery-signals", expose: true },
  async (params: CreateDiscoverySignalParams): Promise<DiscoverySignal> => {
    if (!params.projectId || !params.signalType || !params.source) {
      throw APIError.invalidArgument("projectId, signalType, and source are required");
    }
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
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
);

export const getDiscoverySignal = api(
  { method: "GET", path: "/operations/strategy/discovery-signals/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<DiscoverySignal> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .select()
      .from(discoverySignals)
      .where(and(eq(discoverySignals.id, BigInt(id)), eq(discoverySignals.workspaceId, wsId), isNull(discoverySignals.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound("Discovery signal not found");
    return toDiscoverySignal(row);
  }
);

export const listDiscoverySignals = api(
  { method: "GET", path: "/operations/strategy/discovery-signals", expose: true },
  async (params: ListDiscoverySignalsParams): Promise<{ items: DiscoverySignal[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
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
);

export const updateDiscoverySignal = api(
  { method: "PATCH", path: "/operations/strategy/discovery-signals/:id", expose: true },
  async (params: UpdateDiscoverySignalParams): Promise<DiscoverySignal> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const updateValues: Record<string, any> = { updatedAt: new Date() };
    if (params.signalType !== undefined) updateValues.signalType = params.signalType;
    if (params.payload !== undefined) updateValues.payload = params.payload;
    if (params.source !== undefined) updateValues.source = params.source;

    const [row] = await db
      .update(discoverySignals)
      .set(updateValues)
      .where(and(eq(discoverySignals.id, BigInt(params.id)), eq(discoverySignals.workspaceId, wsId), isNull(discoverySignals.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound("Discovery signal not found");
    return toDiscoverySignal(row);
  }
);

export const deleteDiscoverySignal = api(
  { method: "DELETE", path: "/operations/strategy/discovery-signals/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .update(discoverySignals)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(discoverySignals.id, BigInt(id)), eq(discoverySignals.workspaceId, wsId), isNull(discoverySignals.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound("Discovery signal not found");
    return { success: true };
  }
);
