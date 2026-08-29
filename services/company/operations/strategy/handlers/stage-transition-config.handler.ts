import { api, APIError, Header } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { TenantContext } from "../../../shared/types/tenant_context";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { generateSnowflake } from "../../../shared/services/snowflake.service";

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

export interface CreateStageTransitionParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  fromStage: string;
  toStage: string;
  policyId?: string | number;
  allowed?: boolean;
}

export interface ListStageTransitionsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

function toStageTransition(row: typeof stageTransitionPolicies.$inferSelect): StageTransition {
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

export const createStageTransition = api(
  { method: "POST", path: "/operations/strategy/stage-transitions", expose: true },
  async (params: CreateStageTransitionParams): Promise<StageTransition> => {
    if (!params.fromStage || !params.toStage) {
      throw APIError.invalidArgument("fromStage and toStage are required");
    }
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
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
);

export const getStageTransition = api(
  { method: "GET", path: "/operations/strategy/stage-transitions/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<StageTransition> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .select()
      .from(stageTransitionPolicies)
      .where(and(eq(stageTransitionPolicies.id, BigInt(id)), eq(stageTransitionPolicies.workspaceId, wsId), isNull(stageTransitionPolicies.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound("Stage transition not found");
    return toStageTransition(row);
  }
);

export const listStageTransitions = api(
  { method: "GET", path: "/operations/strategy/stage-transitions", expose: true },
  async (params: ListStageTransitionsParams): Promise<{ items: StageTransition[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const conditions = [eq(stageTransitionPolicies.workspaceId, wsId), isNull(stageTransitionPolicies.deletedAt)];

    const rows = await db
      .select()
      .from(stageTransitionPolicies)
      .where(and(...conditions));

    return {
      items: rows.map(toStageTransition),
    };
  }
);

export const deleteStageTransition = api(
  { method: "DELETE", path: "/operations/strategy/stage-transitions/:id", expose: true },
  async ({ authorization, workspaceId, id }: { authorization?: Header<"Authorization">; workspaceId: Header<"X-Workspace-Id">; id: string }): Promise<{ success: boolean }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    const wsId = BigInt(ctx.workspaceId);

    const [row] = await db
      .update(stageTransitionPolicies)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(stageTransitionPolicies.id, BigInt(id)), eq(stageTransitionPolicies.workspaceId, wsId), isNull(stageTransitionPolicies.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound("Stage transition not found");
    return { success: true };
  }
);
