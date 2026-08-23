import { api, APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";

const { stageTransitions } = schema;

export interface StageTransition {
  id: number;
  companyId: number;
  workspaceId: number;
  fromStage: string;
  toStage: string;
  policyId: number | null;
  allowed: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface CreateStageTransitionParams {
  companyId: number;
  workspaceId: number;
  fromStage: string;
  toStage: string;
  policyId?: number;
  allowed?: boolean;
}

export interface ListStageTransitionsParams {
  workspaceId?: number;
  companyId?: number;
}

export const createStageTransition = api(
  { method: "POST", path: "/operations/strategy/stage-transitions", expose: true },
  async (params: CreateStageTransitionParams): Promise<StageTransition> => {
    if (!params.workspaceId || !params.companyId || !params.fromStage || !params.toStage) {
      throw APIError.invalidArgument("companyId, workspaceId, fromStage, and toStage are required");
    }

    const [row] = await db
      .insert(stageTransitions)
      .values({
        companyId: BigInt(params.companyId),
        workspaceId: BigInt(params.workspaceId),
        fromStage: params.fromStage,
        toStage: params.toStage,
        policyId: params.policyId ? BigInt(params.policyId) : null,
        allowed: params.allowed ?? true,
      })
      .returning();

    if (!row) throw APIError.internal("failed to create stage transition");

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      fromStage: row.fromStage,
      toStage: row.toStage,
      policyId: row.policyId ? Number(row.policyId) : null,
      allowed: row.allowed,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const getStageTransition = api(
  { method: "GET", path: "/operations/strategy/stage-transitions/:id", expose: true },
  async ({ id }: { id: number }): Promise<StageTransition> => {
    const [row] = await db
      .select()
      .from(stageTransitions)
      .where(and(eq(stageTransitions.id, BigInt(id)), isNull(stageTransitions.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound(`stage transition with id ${id} not found`);

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      fromStage: row.fromStage,
      toStage: row.toStage,
      policyId: row.policyId ? Number(row.policyId) : null,
      allowed: row.allowed,
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const listStageTransitions = api(
  { method: "GET", path: "/operations/strategy/stage-transitions", expose: true },
  async (params: ListStageTransitionsParams): Promise<{ items: StageTransition[] }> => {
    const conditions = [isNull(stageTransitions.deletedAt)];

    if (params.workspaceId) {
      conditions.push(eq(stageTransitions.workspaceId, BigInt(params.workspaceId)));
    }
    if (params.companyId) {
      conditions.push(eq(stageTransitions.companyId, BigInt(params.companyId)));
    }

    const rows = await db
      .select()
      .from(stageTransitions)
      .where(and(...conditions));

    return {
      items: rows.map((row) => ({
        id: Number(row.id),
        companyId: Number(row.companyId),
        workspaceId: Number(row.workspaceId),
        fromStage: row.fromStage,
        toStage: row.toStage,
        policyId: row.policyId ? Number(row.policyId) : null,
        allowed: row.allowed,
        createdAt: row.createdAt.toISOString(),
        updatedAt: row.updatedAt.toISOString(),
      })),
    };
  }
);

export const deleteStageTransition = api(
  { method: "DELETE", path: "/operations/strategy/stage-transitions/:id", expose: true },
  async ({ id }: { id: number }): Promise<{ success: boolean }> => {
    const [row] = await db
      .update(stageTransitions)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(stageTransitions.id, BigInt(id)), isNull(stageTransitions.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`stage transition with id ${id} not found`);
    return { success: true };
  }
);
