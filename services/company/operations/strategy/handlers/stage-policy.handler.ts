import { api, APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { resolveWorkspaceId } from "../../../shared/services/workspace-resolver.service";

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

export interface CreateStagePolicyParams {
  workspaceId?: string | number;
  companyId?: string | number;
  stageKey: string;
  requirements?: any[];
  minimumEvidenceScore?: string | number;
  blockingRiskRules?: any[];
}

export interface ListStagePoliciesParams {
  workspaceId?: string | number;
  companyId?: string | number;
  stageKey?: string;
}

export interface UpdateStagePolicyParams {
  requirements?: any[];
  minimumEvidenceScore?: string | number;
  blockingRiskRules?: any[];
}

function toStagePolicy(row: typeof stagePolicies.$inferSelect): StagePolicy {
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

export const createStagePolicy = api(
  { method: "POST", path: "/operations/strategy/stage-policies", expose: true },
  async (params: CreateStagePolicyParams): Promise<StagePolicy> => {
    if (!params.stageKey) {
      throw APIError.invalidArgument("stageKey is required");
    }
    const workspaceId = await resolveWorkspaceId({ workspaceId: params.workspaceId, companyId: params.companyId });

    const [row] = await db
      .insert(stagePolicies)
      .values({
        id: generateSnowflake(),
        workspaceId,
        stageKey: params.stageKey,
        requirements: params.requirements ?? [],
        minimumEvidenceScore: typeof params.minimumEvidenceScore === "string" ? parseFloat(params.minimumEvidenceScore) : (params.minimumEvidenceScore ?? 0.0),
        blockingRiskRules: params.blockingRiskRules ?? [],
      })
      .returning();

    if (!row) throw APIError.internal("failed to create stage policy");
    return toStagePolicy(row);
  }
);

export const getStagePolicy = api(
  { method: "GET", path: "/operations/strategy/stage-policies/:id", expose: true },
  async ({ id }: { id: string }): Promise<StagePolicy> => {
    const [row] = await db
      .select()
      .from(stagePolicies)
      .where(and(eq(stagePolicies.id, BigInt(id)), isNull(stagePolicies.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound(`stage policy with id ${id} not found`);
    return toStagePolicy(row);
  }
);

export const listStagePolicies = api(
  { method: "GET", path: "/operations/strategy/stage-policies", expose: true },
  async (params: ListStagePoliciesParams): Promise<{ items: StagePolicy[] }> => {
    const conditions = [isNull(stagePolicies.deletedAt)];

    if (params.workspaceId || params.companyId) {
      const workspaceId = await resolveWorkspaceId({ workspaceId: params.workspaceId, companyId: params.companyId });
      conditions.push(eq(stagePolicies.workspaceId, workspaceId));
    }
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
);

export const updateStagePolicy = api(
  { method: "PATCH", path: "/operations/strategy/stage-policies/:id", expose: true },
  async ({ id, ...params }: UpdateStagePolicyParams & { id: string }): Promise<StagePolicy> => {
    const updateValues: Record<string, any> = { updatedAt: new Date() };
    if (params.requirements !== undefined) updateValues.requirements = params.requirements;
    if (params.minimumEvidenceScore !== undefined) {
      updateValues.minimumEvidenceScore = typeof params.minimumEvidenceScore === "string" ? parseFloat(params.minimumEvidenceScore) : params.minimumEvidenceScore;
    }
    if (params.blockingRiskRules !== undefined) updateValues.blockingRiskRules = params.blockingRiskRules;

    const [row] = await db
      .update(stagePolicies)
      .set(updateValues)
      .where(and(eq(stagePolicies.id, BigInt(id)), isNull(stagePolicies.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`stage policy with id ${id} not found`);
    return toStagePolicy(row);
  }
);

export const deleteStagePolicy = api(
  { method: "DELETE", path: "/operations/strategy/stage-policies/:id", expose: true },
  async ({ id }: { id: string }): Promise<{ success: boolean }> => {
    const [row] = await db
      .update(stagePolicies)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(stagePolicies.id, BigInt(id)), isNull(stagePolicies.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`stage policy with id ${id} not found`);
    return { success: true };
  }
);
