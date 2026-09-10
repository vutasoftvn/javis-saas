import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { assertLifecyclePrivileged } from "../strategy/services/lifecycle-authorization.service";

const { projects, projectLifecycleEvents } = schema;

// M4 §3 — chuỗi lifecycle Project, thứ tự cố định. Lifecycle là context phát
// triển; KHÔNG có progression tự động — chỉ transition thủ công do người có
// quyền thực hiện.
export const PROJECT_LIFECYCLE_STAGES = [
  "P0_DISCOVERY",
  "P1_PROBLEM_VALIDATION",
  "P2_SOLUTION_VALIDATION",
  "P3_BUILD_VALIDATE",
  "P4_GO_TO_MARKET",
  "P5_OPERATE_GROWTH",
  "P6_SCALE_GOVERN",
] as const;

export type ProjectLifecycleStage = (typeof PROJECT_LIFECYCLE_STAGES)[number];

export interface TransitionProjectLifecycleInput {
  toStage: string;
  expectedStageVersion: number;
  rationale?: string;
}

export interface ProjectLifecycleState {
  projectId: string;
  workspaceId: string;
  lifecycleStage: string;
  stageVersion: number;
  stageEnteredAt: string | null;
}

export interface ProjectLifecycleEvent {
  id: string;
  fromStage: string;
  toStage: string;
  fromStageVersion: number;
  actorMemberId: string | null;
  rationale: string | null;
  createdAt: string;
}

function stageIndex(stage: string): number {
  return (PROJECT_LIFECYCLE_STAGES as readonly string[]).indexOf(stage);
}

/**
 * Chuyển lifecycle stage của Project trong một transaction với optimistic
 * locking trên `stage_version`. Tiến tối đa 1 bậc; lùi bất kỳ bậc nào nhưng bắt
 * buộc có `rationale`. Không gọi gate framework, không gọi model.
 */
export async function transitionProjectLifecycle(
  ctx: TenantContext,
  projectId: string | number,
  input: TransitionProjectLifecycleInput
): Promise<ProjectLifecycleState> {
  assertLifecyclePrivileged(ctx.membershipRole, "transitionProjectLifecycle");

  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);
  const toStage = input.toStage;

  if (stageIndex(toStage) === -1) {
    throw APIError.invalidArgument(`Invalid project lifecycle stage '${toStage}'`);
  }

  return db.transaction(async (tx) => {
    const [proj] = await tx
      .select({
        lifecycleStage: projects.lifecycleStage,
        stageVersion: projects.stageVersion,
      })
      .from(projects)
      .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)))
      .limit(1);

    if (!proj) {
      throw APIError.notFound(`Project ${projectId} not found in workspace`);
    }

    const fromStage = proj.lifecycleStage;
    if (fromStage === toStage) {
      throw APIError.invalidArgument("Project is already at the requested lifecycle stage");
    }

    const delta = stageIndex(toStage) - stageIndex(fromStage);
    if (delta > 1) {
      throw APIError.invalidArgument("Project lifecycle can advance at most one stage at a time");
    }
    if (delta < 0 && (!input.rationale || input.rationale.trim().length === 0)) {
      throw APIError.invalidArgument("Moving a project lifecycle backward requires a rationale");
    }

    const fromStageVersion = proj.stageVersion;
    const nextVersion = input.expectedStageVersion + 1;

    const updated = await tx
      .update(projects)
      .set({
        lifecycleStage: toStage,
        stageVersion: nextVersion,
        stageEnteredAt: new Date(),
        updatedAt: new Date(),
      })
      .where(
        and(
          eq(projects.id, pId),
          eq(projects.workspaceId, wsId),
          eq(projects.stageVersion, input.expectedStageVersion)
        )
      )
      .returning({
        lifecycleStage: projects.lifecycleStage,
        stageVersion: projects.stageVersion,
        stageEnteredAt: projects.stageEnteredAt,
      });

    if (updated.length !== 1) {
      throw APIError.aborted("Project lifecycle changed; reload before retrying");
    }

    await tx.insert(projectLifecycleEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      projectId: pId,
      fromStage,
      toStage,
      fromStageVersion,
      actorMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
      rationale: input.rationale ?? null,
    });

    const row = updated[0];
    return {
      projectId: pId.toString(),
      workspaceId: wsId.toString(),
      lifecycleStage: row.lifecycleStage,
      stageVersion: row.stageVersion,
      stageEnteredAt: row.stageEnteredAt ? row.stageEnteredAt.toISOString() : null,
    };
  });
}

export async function listProjectLifecycleEvents(
  ctx: TenantContext,
  projectId: string | number
): Promise<{ items: ProjectLifecycleEvent[] }> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);

  const rows = await db
    .select()
    .from(projectLifecycleEvents)
    .where(and(eq(projectLifecycleEvents.projectId, pId), eq(projectLifecycleEvents.workspaceId, wsId)));

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
