import { api, APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";

const { discoverySignals } = schema;

export interface DiscoverySignal {
  id: number;
  companyId: number;
  workspaceId: number;
  projectId: number;
  signalType: string;
  payload: Record<string, any>;
  source: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateDiscoverySignalParams {
  companyId: number;
  workspaceId: number;
  projectId: number;
  signalType: string;
  payload?: Record<string, any>;
  source: string;
}

export interface ListDiscoverySignalsParams {
  workspaceId?: number;
  companyId?: number;
  projectId?: number;
  signalType?: string;
}

export interface UpdateDiscoverySignalParams {
  signalType?: string;
  payload?: Record<string, any>;
  source?: string;
}

export const createDiscoverySignal = api(
  { method: "POST", path: "/operations/strategy/discovery-signals", expose: true },
  async (params: CreateDiscoverySignalParams): Promise<DiscoverySignal> => {
    if (!params.workspaceId || !params.companyId || !params.projectId || !params.signalType || !params.source) {
      throw APIError.invalidArgument("companyId, workspaceId, projectId, signalType, and source are required");
    }

    const [row] = await db
      .insert(discoverySignals)
      .values({
        companyId: BigInt(params.companyId),
        workspaceId: BigInt(params.workspaceId),
        projectId: BigInt(params.projectId),
        signalType: params.signalType,
        payload: params.payload ?? {},
        source: params.source,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create discovery signal");

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      projectId: Number(row.projectId),
      signalType: row.signalType,
      payload: row.payload as Record<string, any>,
      source: row.source,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const getDiscoverySignal = api(
  { method: "GET", path: "/operations/strategy/discovery-signals/:id", expose: true },
  async ({ id }: { id: number }): Promise<DiscoverySignal> => {
    const [row] = await db
      .select()
      .from(discoverySignals)
      .where(and(eq(discoverySignals.id, BigInt(id)), isNull(discoverySignals.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound(`discovery signal with id ${id} not found`);

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      projectId: Number(row.projectId),
      signalType: row.signalType,
      payload: row.payload as Record<string, any>,
      source: row.source,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const listDiscoverySignals = api(
  { method: "GET", path: "/operations/strategy/discovery-signals", expose: true },
  async (params: ListDiscoverySignalsParams): Promise<{ items: DiscoverySignal[] }> => {
    const conditions = [isNull(discoverySignals.deletedAt)];

    if (params.workspaceId) {
      conditions.push(eq(discoverySignals.workspaceId, BigInt(params.workspaceId)));
    }
    if (params.companyId) {
      conditions.push(eq(discoverySignals.companyId, BigInt(params.companyId)));
    }
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
      items: rows.map((row) => ({
        id: Number(row.id),
        companyId: Number(row.companyId),
        workspaceId: Number(row.workspaceId),
        projectId: Number(row.projectId),
        signalType: row.signalType,
        payload: row.payload as Record<string, any>,
        source: row.source,
        createdAt: row.createdAt.toISOString(),
        updatedAt: row.updatedAt.toISOString(),
      })),
    };
  }
);

export const updateDiscoverySignal = api(
  { method: "PATCH", path: "/operations/strategy/discovery-signals/:id", expose: true },
  async ({ id, ...params }: UpdateDiscoverySignalParams & { id: number }): Promise<DiscoverySignal> => {
    const updateValues: Record<string, any> = { updatedAt: new Date() };
    if (params.signalType !== undefined) updateValues.signalType = params.signalType;
    if (params.payload !== undefined) updateValues.payload = params.payload;
    if (params.source !== undefined) updateValues.source = params.source;

    const [row] = await db
      .update(discoverySignals)
      .set(updateValues)
      .where(and(eq(discoverySignals.id, BigInt(id)), isNull(discoverySignals.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`discovery signal with id ${id} not found`);

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      projectId: Number(row.projectId),
      signalType: row.signalType,
      payload: row.payload as Record<string, any>,
      source: row.source,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const deleteDiscoverySignal = api(
  { method: "DELETE", path: "/operations/strategy/discovery-signals/:id", expose: true },
  async ({ id }: { id: number }): Promise<{ success: boolean }> => {
    const [row] = await db
      .update(discoverySignals)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(discoverySignals.id, BigInt(id)), isNull(discoverySignals.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`discovery signal with id ${id} not found`);
    return { success: true };
  }
);
