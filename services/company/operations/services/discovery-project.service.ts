import { APIError } from "encore.dev/api";
import { eq, and, isNull, ne, isNotNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { projects, okrObjectives, goals } = schema;

async function assertCompanyObjective(wsId: bigint, objectiveId: bigint): Promise<void> {
  const [row] = await db
    .select({ scope: okrObjectives.scope })
    .from(okrObjectives)
    .where(
      and(
        eq(okrObjectives.id, objectiveId),
        eq(okrObjectives.workspaceId, wsId),
        isNull(okrObjectives.deletedAt),
      ),
    )
    .limit(1);
  if (!row) throw APIError.notFound("Không tìm thấy Objective trong workspace này.");
  if (row.scope !== "company") {
    throw APIError.invalidArgument("Dự án chỉ có thể liên kết với Objective cấp công ty (company).");
  }
}

// parentId = null: objective cha chưa tồn tại → mọi child đã căn chỉnh đều xung đột.
async function assertNoConflictingChildren(wsId: bigint, projectId: bigint, parentId: bigint | null): Promise<void> {
  const conflicts = await db
    .select({ id: okrObjectives.id })
    .from(okrObjectives)
    .where(
      and(
        eq(okrObjectives.workspaceId, wsId),
        eq(okrObjectives.projectId, projectId),
        isNotNull(okrObjectives.parentObjectiveId),
        parentId === null ? undefined : ne(okrObjectives.parentObjectiveId, parentId),
      ),
    )
    .limit(1);
  if (conflicts.length > 0) {
    throw APIError.failedPrecondition(
      "Dự án đang có objective căn chỉnh với parent objective khác; hãy đổi parent trước khi liên kết.",
    );
  }
}

export type ProjectTriageAction = "link" | "mark_rd" | "archive" | "roll_to_new_goal";

export async function listPendingReviewProjectsService(workspaceId: string): Promise<{
  projects: Array<{
    id: string;
    title: string;
    description: string | null;
    origin: string | null;
    linkStatus: string | null;
    createdAt: string;
  }>;
}> {
  const wsId = BigInt(workspaceId);

  const rows = await db
    .select()
    .from(projects)
    .where(
      and(
        eq(projects.workspaceId, wsId),
        eq(projects.linkStatus, "pending_review")
      )
    );

  return {
    projects: rows.map((r) => ({
      id: r.id.toString(),
      title: r.title,
      description: r.description,
      origin: r.origin,
      linkStatus: r.linkStatus,
      createdAt: r.createdAt.toISOString(),
    })),
  };
}

export async function triageProjectService(params: {
  workspaceId: string;
  projectId: string;
  action: ProjectTriageAction;
  targetObjectiveId?: string;
  newGoalId?: string;
  newObjectiveTitle?: string;
}): Promise<{ success: boolean; projectId: string; action: string }> {
  const wsId = BigInt(params.workspaceId);
  const pId = BigInt(params.projectId);

  const [project] = await db
    .select()
    .from(projects)
    .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!project) {
    throw APIError.notFound("Không tìm thấy dự án.");
  }

  switch (params.action) {
    case "link": {
      if (!params.targetObjectiveId) {
        throw APIError.invalidArgument("Cần cung cấp targetObjectiveId để liên kết dự án.");
      }
      const objId = BigInt(params.targetObjectiveId);
      await assertCompanyObjective(wsId, objId);
      await assertNoConflictingChildren(wsId, pId, objId);
      await db.update(projects).set({ objectiveId: objId, linkStatus: "linked" }).where(eq(projects.id, pId));
      break;
    }

    case "mark_rd": {
      await db
        .update(projects)
        .set({
          linkStatus: "intentionally_unlinked",
        })
        .where(eq(projects.id, pId));
      break;
    }

    case "archive": {
      await db
        .update(projects)
        .set({
          status: "ARCHIVED",
        })
        .where(eq(projects.id, pId));
      break;
    }

    case "roll_to_new_goal": {
      if (!params.newGoalId || !params.newObjectiveTitle) {
        throw APIError.invalidArgument("Cần cung cấp newGoalId và newObjectiveTitle để đưa dự án vào chu kỳ mới.");
      }
      const newGoalId = BigInt(params.newGoalId);
      const [goal] = await db
        .select({ id: goals.id })
        .from(goals)
        .where(and(eq(goals.id, newGoalId), eq(goals.workspaceId, wsId)))
        .limit(1);
      if (!goal) throw APIError.notFound("Không tìm thấy Goal trong workspace này.");

      await assertNoConflictingChildren(wsId, pId, null);

      const objectiveId = generateSnowflake();
      await db.transaction(async (tx) => {
        await tx.insert(okrObjectives).values({
          id: objectiveId,
          workspaceId: wsId,
          scope: "company",
          goalId: newGoalId,
          title: params.newObjectiveTitle!,
        });
        await tx.update(projects).set({ objectiveId, linkStatus: "linked" }).where(eq(projects.id, pId));
      });
      break;
    }

    default:
      throw APIError.invalidArgument(`Hành động triage không hợp lệ: ${params.action}`);
  }

  return { success: true, projectId: params.projectId, action: params.action };
}
