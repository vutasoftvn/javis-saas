import { api, APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";

const { stagePolicies } = schema;

export interface StagePolicy {
  id: number;
  companyId: number;
  workspaceId: number;
  stageKey: string;
  requirements: any[];
  minimumEvidenceScore: number;
  blockingRiskRules: any[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateStagePolicyParams {
  companyId: number;
  workspaceId: number;
  stageKey: string;
  requirements?: any[];
  minimumEvidenceScore?: number;
  blockingRiskRules?: any[];
}

export interface ListStagePoliciesParams {
  workspaceId?: number;
  companyId?: number;
  stageKey?: string;
}

export interface UpdateStagePolicyParams {
  requirements?: any[];
  minimumEvidenceScore?: number;
  blockingRiskRules?: any[];
}

export const createStagePolicy = api(
  { method: "POST", path: "/operations/strategy/stage-policies", expose: true },
  async (params: CreateStagePolicyParams): Promise<StagePolicy> => {
    if (!params.workspaceId || !params.companyId || !params.stageKey) {
      throw APIError.invalidArgument("companyId, workspaceId, and stageKey are required");
    }

    const [row] = await db
      .insert(stagePolicies)
      .values({
        companyId: BigInt(params.companyId),
        workspaceId: BigInt(params.workspaceId),
        stageKey: params.stageKey,
        requirements: params.requirements ?? [],
        minimumEvidenceScore: params.minimumEvidenceScore ?? 0.0,
        blockingRiskRules: params.blockingRiskRules ?? [],
      })
      .returning();

    if (!row) throw APIError.internal("failed to create stage policy");

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      stageKey: row.stageKey,
      requirements: row.requirements as any[],
      minimumEvidenceScore: row.minimumEvidenceScore,
      blockingRiskRules: row.blockingRiskRules as any[],
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const getStagePolicy = api(
  { method: "GET", path: "/operations/strategy/stage-policies/:id", expose: true },
  async ({ id }: { id: number }): Promise<StagePolicy> => {
    const [row] = await db
      .select()
      .from(stagePolicies)
      .where(and(eq(stagePolicies.id, BigInt(id)), isNull(stagePolicies.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound(`stage policy with id ${id} not found`);

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      stageKey: row.stageKey,
      requirements: row.requirements as any[],
      minimumEvidenceScore: row.minimumEvidenceScore,
      blockingRiskRules: row.blockingRiskRules as any[],
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const listStagePolicies = api(
  { method: "GET", path: "/operations/strategy/stage-policies", expose: true },
  async (params: ListStagePoliciesParams): Promise<{ items: StagePolicy[] }> => {
    const conditions = [isNull(stagePolicies.deletedAt)];

    if (params.workspaceId) {
      conditions.push(eq(stagePolicies.workspaceId, BigInt(params.workspaceId)));
    }
    if (params.companyId) {
      conditions.push(eq(stagePolicies.companyId, BigInt(params.companyId)));
    }
    if (params.stageKey) {
      conditions.push(eq(stagePolicies.stageKey, params.stageKey));
    }

    const rows = await db
      .select()
      .from(stagePolicies)
      .where(and(...conditions));

    return {
      items: rows.map((row) => ({
        id: Number(row.id),
        companyId: Number(row.companyId),
        workspaceId: Number(row.workspaceId),
        stageKey: row.stageKey,
        requirements: row.requirements as any[],
        minimumEvidenceScore: row.minimumEvidenceScore,
        blockingRiskRules: row.blockingRiskRules as any[],
        createdAt: row.createdAt.toISOString(),
        updatedAt: row.updatedAt.toISOString(),
      })),
    };
  }
);

export const updateStagePolicy = api(
  { method: "PATCH", path: "/operations/strategy/stage-policies/:id", expose: true },
  async ({ id, ...params }: UpdateStagePolicyParams & { id: number }): Promise<StagePolicy> => {
    const updateValues: Record<string, any> = { updatedAt: new Date() };
    if (params.requirements !== undefined) updateValues.requirements = params.requirements;
    if (params.minimumEvidenceScore !== undefined) updateValues.minimumEvidenceScore = params.minimumEvidenceScore;
    if (params.blockingRiskRules !== undefined) updateValues.blockingRiskRules = params.blockingRiskRules;

    const [row] = await db
      .update(stagePolicies)
      .set(updateValues)
      .where(and(eq(stagePolicies.id, BigInt(id)), isNull(stagePolicies.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`stage policy with id ${id} not found`);

    return {
      id: Number(row.id),
      companyId: Number(row.companyId),
      workspaceId: Number(row.workspaceId),
      stageKey: row.stageKey,
      requirements: row.requirements as any[],
      minimumEvidenceScore: row.minimumEvidenceScore,
      blockingRiskRules: row.blockingRiskRules as any[],
      createdAt: row.createdAt.toISOString(),
      updatedAt: row.updatedAt.toISOString(),
    };
  }
);

export const deleteStagePolicy = api(
  { method: "DELETE", path: "/operations/strategy/stage-policies/:id", expose: true },
  async ({ id }: { id: number }): Promise<{ success: boolean }> => {
    const [row] = await db
      .update(stagePolicies)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(stagePolicies.id, BigInt(id)), isNull(stagePolicies.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`stage policy with id ${id} not found`);
    return { success: true };
  }
);
