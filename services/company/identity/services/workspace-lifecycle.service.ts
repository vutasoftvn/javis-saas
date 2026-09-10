import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import { assertLifecyclePrivileged } from "../../operations/strategy/services/lifecycle-authorization.service";

const { identityWorkspaces, identityWorkspaceLifecycleEvents } = schema;

// M4 §1 — chuỗi lifecycle Workspace, thứ tự cố định. Không progression tự động.
export const WORKSPACE_LIFECYCLE_STAGES = [
  "W0_IDEA",
  "W1_PROBLEM_VALIDATION",
  "W2_SOLUTION_VALIDATION",
  "W3_MVP_BUILD",
  "W4_PRODUCT_MARKET_FIT",
  "W5_SCALE",
] as const;

export type WorkspaceLifecycleStage = (typeof WORKSPACE_LIFECYCLE_STAGES)[number];

export interface TransitionWorkspaceLifecycleInput {
  toStage: string;
  expectedStageVersion: number;
  rationale?: string;
}

export interface WorkspaceLifecycleState {
  workspaceId: string;
  lifecycleStage: string;
  stageVersion: number;
  stageEnteredAt: string | null;
}

export interface WorkspaceLifecycleEvent {
  id: string;
  fromStage: string;
  toStage: string;
  fromStageVersion: number;
  actorMemberId: string | null;
  rationale: string | null;
  createdAt: string;
}

function stageIndex(stage: string): number {
  return (WORKSPACE_LIFECYCLE_STAGES as readonly string[]).indexOf(stage);
}

/**
 * Chuyển lifecycle stage của Workspace với optimistic locking trên
 * `stage_version`. Tiến tối đa 1 bậc; lùi bắt buộc có `rationale`. Không gate,
 * không model, không tự động.
 */
export async function transitionWorkspaceLifecycle(
  ctx: TenantContext,
  workspaceId: string | number,
  input: TransitionWorkspaceLifecycleInput
): Promise<WorkspaceLifecycleState> {
  assertLifecyclePrivileged(ctx.membershipRole, "transitionWorkspaceLifecycle");

  const wsId = BigInt(workspaceId);
  if (wsId.toString() !== ctx.workspaceId) {
    throw APIError.permissionDenied("Cannot transition another workspace's lifecycle");
  }

  const toStage = input.toStage;
  if (stageIndex(toStage) === -1) {
    throw APIError.invalidArgument(`Invalid workspace lifecycle stage '${toStage}'`);
  }

  return db.transaction(async (tx) => {
    const [ws] = await tx
      .select({
        lifecycleStage: identityWorkspaces.lifecycleStage,
        stageVersion: identityWorkspaces.stageVersion,
      })
      .from(identityWorkspaces)
      .where(eq(identityWorkspaces.id, wsId))
      .limit(1);

    if (!ws) {
      throw APIError.notFound(`Workspace ${workspaceId} not found`);
    }

    const fromStage = ws.lifecycleStage;
    if (fromStage === toStage) {
      throw APIError.invalidArgument("Workspace is already at the requested lifecycle stage");
    }

    const delta = stageIndex(toStage) - stageIndex(fromStage);
    if (delta > 1) {
      throw APIError.invalidArgument("Workspace lifecycle can advance at most one stage at a time");
    }
    if (delta < 0 && (!input.rationale || input.rationale.trim().length === 0)) {
      throw APIError.invalidArgument("Moving a workspace lifecycle backward requires a rationale");
    }

    const fromStageVersion = ws.stageVersion;
    const nextVersion = input.expectedStageVersion + 1;

    const updated = await tx
      .update(identityWorkspaces)
      .set({
        lifecycleStage: toStage,
        stageVersion: nextVersion,
        stageEnteredAt: new Date(),
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(identityWorkspaces.id, wsId),
          eq(identityWorkspaces.stageVersion, input.expectedStageVersion)
        )
      )
      .returning({
        lifecycleStage: identityWorkspaces.lifecycleStage,
        stageVersion: identityWorkspaces.stageVersion,
        stageEnteredAt: identityWorkspaces.stageEnteredAt,
      });

    if (updated.length !== 1) {
      throw APIError.aborted("Workspace lifecycle changed; reload before retrying");
    }

    await tx.insert(identityWorkspaceLifecycleEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      fromStage,
      toStage,
      fromStageVersion,
      actorMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
      rationale: input.rationale ?? null,
    });

    const row = updated[0];
    return {
      workspaceId: wsId.toString(),
      lifecycleStage: row.lifecycleStage,
      stageVersion: row.stageVersion,
      stageEnteredAt: row.stageEnteredAt ? row.stageEnteredAt.toISOString() : null,
    };
  });
}

export async function listWorkspaceLifecycleEvents(
  ctx: TenantContext,
  workspaceId: string | number
): Promise<{ items: WorkspaceLifecycleEvent[] }> {
  const wsId = BigInt(workspaceId);
  if (wsId.toString() !== ctx.workspaceId) {
    throw APIError.permissionDenied("Cannot read another workspace's lifecycle history");
  }

  const rows = await db
    .select()
    .from(identityWorkspaceLifecycleEvents)
    .where(eq(identityWorkspaceLifecycleEvents.workspaceId, wsId));

  return {
    items: rows
      .map((r) => ({
        id: r.id.toString(),
        fromStage: r.fromStage,
        toStage: r.toStage,
        fromStageVersion: r.fromStageVersion,
        actorMemberId: r.actorMemberId ? r.actorMemberId.toString() : null,
        rationale: r.rationale,
        createdAt: r.createdAt.toISOString(),
      }))
      .sort((a, b) => a.createdAt.localeCompare(b.createdAt)),
  };
}
