import { APIError } from "encore.dev/api";
import { eq, and, inArray } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { getProjectInWorkspace } from "./project-access.service";

const { taskProjects, okrObjectiveProjects, tasks, okrObjectives, projects } = schema;

/**
 * Link một task tới danh sách projects trong workspace của nó.
 * Xác nhận task tồn tại và thuộc workspace, rồi xác nhận từng project
 * tồn tại và thuộc workspace. Nếu project nào ở workspace khác → notFound.
 * Insert idempotent qua onConflictDoNothing().
 */
export async function linkTaskProjects(
  ctx: TenantContext,
  taskId: string,
  projectIds: string[]
): Promise<void> {
  const wsId = BigInt(ctx.workspaceId);
  const taskIdBig = BigInt(taskId);

  // Xác nhận task tồn tại và thuộc workspace này
  const [taskRow] = await db
    .select()
    .from(tasks)
    .where(and(eq(tasks.id, taskIdBig), eq(tasks.workspaceId, wsId)))
    .limit(1);

  if (!taskRow) throw APIError.notFound("Task not found");

  // Nếu không có project nào → no-op
  if (projectIds.length === 0) {
    return;
  }

  // Xác nhận từng project tồn tại và thuộc workspace này
  for (const projectId of projectIds) {
    await getProjectInWorkspace(projectId, ctx);
  }

  // Insert tất cả (với onConflictDoNothing để idempotent)
  const values = projectIds.map((projectId) => ({
    workspaceId: wsId,
    taskId: taskIdBig,
    projectId: BigInt(projectId),
    createdAt: new Date(),
  }));

  await db.insert(taskProjects).values(values).onConflictDoNothing();
}

/**
 * List tất cả projects được link tới một task.
 * Returns danh sách projectIds (strings). Nếu task không tồn tại
 * hoặc không phải workspace này → notFound.
 */
export async function listTaskProjects(ctx: TenantContext, taskId: string): Promise<string[]> {
  const wsId = BigInt(ctx.workspaceId);
  const taskIdBig = BigInt(taskId);

  // Xác nhận task tồn tại và thuộc workspace này
  const [taskRow] = await db
    .select()
    .from(tasks)
    .where(and(eq(tasks.id, taskIdBig), eq(tasks.workspaceId, wsId)))
    .limit(1);

  if (!taskRow) throw APIError.notFound("Task not found");

  // Query và return projectIds
  const rows = await db
    .select({ projectId: taskProjects.projectId })
    .from(taskProjects)
    .where(and(eq(taskProjects.workspaceId, wsId), eq(taskProjects.taskId, taskIdBig)));

  return rows.map((r) => r.projectId.toString());
}

/**
 * Unlink một project từ một task.
 * Nếu task không tồn tại hoặc không phải workspace này → notFound.
 * Nếu link không tồn tại, xem như no-op (không lỗi).
 */
export async function unlinkTaskProject(ctx: TenantContext, taskId: string, projectId: string): Promise<void> {
  const wsId = BigInt(ctx.workspaceId);
  const taskIdBig = BigInt(taskId);
  const projectIdBig = BigInt(projectId);

  // Xác nhận task tồn tại và thuộc workspace này
  const [taskRow] = await db
    .select()
    .from(tasks)
    .where(and(eq(tasks.id, taskIdBig), eq(tasks.workspaceId, wsId)))
    .limit(1);

  if (!taskRow) throw APIError.notFound("Task not found");

  // Delete link
  await db
    .delete(taskProjects)
    .where(
      and(
        eq(taskProjects.workspaceId, wsId),
        eq(taskProjects.taskId, taskIdBig),
        eq(taskProjects.projectId, projectIdBig)
      )
    );
}

/**
 * Link một objective tới danh sách projects trong workspace của nó.
 * Xác nhận objective tồn tại và thuộc workspace, rồi xác nhận từng project
 * tồn tại và thuộc workspace. Nếu project nào ở workspace khác → notFound.
 * Insert idempotent qua onConflictDoNothing().
 */
export async function linkObjectiveProjects(
  ctx: TenantContext,
  objectiveId: string,
  projectIds: string[]
): Promise<void> {
  const wsId = BigInt(ctx.workspaceId);
  const objectiveIdBig = BigInt(objectiveId);

  // Xác nhận objective tồn tại và thuộc workspace này
  const [objectiveRow] = await db
    .select()
    .from(okrObjectives)
    .where(and(eq(okrObjectives.id, objectiveIdBig), eq(okrObjectives.workspaceId, wsId)))
    .limit(1);

  if (!objectiveRow) throw APIError.notFound("Objective not found");

  // Nếu không có project nào → no-op
  if (projectIds.length === 0) {
    return;
  }

  // Xác nhận từng project tồn tại và thuộc workspace này
  for (const projectId of projectIds) {
    await getProjectInWorkspace(projectId, ctx);
  }

  // Insert tất cả (với onConflictDoNothing để idempotent)
  const values = projectIds.map((projectId) => ({
    workspaceId: wsId,
    objectiveId: objectiveIdBig,
    projectId: BigInt(projectId),
    createdAt: new Date(),
  }));

  await db.insert(okrObjectiveProjects).values(values).onConflictDoNothing();
}

/**
 * List tất cả projects được link tới một objective.
 * Returns danh sách projectIds (strings). Nếu objective không tồn tại
 * hoặc không phải workspace này → notFound.
 */
export async function listObjectiveProjects(ctx: TenantContext, objectiveId: string): Promise<string[]> {
  const wsId = BigInt(ctx.workspaceId);
  const objectiveIdBig = BigInt(objectiveId);

  // Xác nhận objective tồn tại và thuộc workspace này
  const [objectiveRow] = await db
    .select()
    .from(okrObjectives)
    .where(and(eq(okrObjectives.id, objectiveIdBig), eq(okrObjectives.workspaceId, wsId)))
    .limit(1);

  if (!objectiveRow) throw APIError.notFound("Objective not found");

  // Query và return projectIds
  const rows = await db
    .select({ projectId: okrObjectiveProjects.projectId })
    .from(okrObjectiveProjects)
    .where(and(eq(okrObjectiveProjects.workspaceId, wsId), eq(okrObjectiveProjects.objectiveId, objectiveIdBig)));

  return rows.map((r) => r.projectId.toString());
}

/**
 * Unlink một project từ một objective.
 * Nếu objective không tồn tại hoặc không phải workspace này → notFound.
 * Nếu link không tồn tại, xem như no-op (không lỗi).
 */
export async function unlinkObjectiveProject(
  ctx: TenantContext,
  objectiveId: string,
  projectId: string
): Promise<void> {
  const wsId = BigInt(ctx.workspaceId);
  const objectiveIdBig = BigInt(objectiveId);
  const projectIdBig = BigInt(projectId);

  // Xác nhận objective tồn tại và thuộc workspace này
  const [objectiveRow] = await db
    .select()
    .from(okrObjectives)
    .where(and(eq(okrObjectives.id, objectiveIdBig), eq(okrObjectives.workspaceId, wsId)))
    .limit(1);

  if (!objectiveRow) throw APIError.notFound("Objective not found");

  // Delete link
  await db
    .delete(okrObjectiveProjects)
    .where(
      and(
        eq(okrObjectiveProjects.workspaceId, wsId),
        eq(okrObjectiveProjects.objectiveId, objectiveIdBig),
        eq(okrObjectiveProjects.projectId, projectIdBig)
      )
    );
}
