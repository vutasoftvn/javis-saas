import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createObjectiveService } from "./goals.service";

const { projects, objectives } = schema;

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
      await db
        .update(projects)
        .set({
          objectiveId: objId,
          linkStatus: "linked",
        })
        .where(eq(projects.id, pId));
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
      // Tạo objective mới trong Goal mới
      const { objectiveId } = await createObjectiveService({
        workspaceId: params.workspaceId,
        goalId: params.newGoalId,
        title: params.newObjectiveTitle,
      });

      // Liên kết dự án vào objective mới
      await db
        .update(projects)
        .set({
          objectiveId: BigInt(objectiveId),
          linkStatus: "linked",
        })
        .where(eq(projects.id, pId));
      break;
    }

    default:
      throw APIError.invalidArgument(`Hành động triage không hợp lệ: ${params.action}`);
  }

  return { success: true, projectId: params.projectId, action: params.action };
}
