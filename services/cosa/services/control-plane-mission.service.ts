import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "./snowflake.service";

const { missions, tasks, assignments } = schema;

/**
 * Mission/Task/Assignment CRUD (Paperclip-inspired, Blueprint V2 §39/§71.1).
 * KHÔNG có consumer production hiện tại — hạ tầng đón đầu, chưa verify bằng
 * Postgres thật. `assignments` atomic checkout dựa vào unique partial index
 * `idx_control_plane_assignments_task_active_lease` (migration 6) — 1 task chỉ
 * có tối đa 1 assignment 'leased' tại 1 thời điểm, DB tự chặn double-checkout
 * qua constraint, không cần SELECT FOR UPDATE riêng ở tầng ứng dụng.
 */

export interface CreateMissionParams {
  tenantId: bigint;
  creatorId: bigint;
  goal: string;
  priority?: number;
  budgetCents?: bigint;
  deadline?: Date;
}

export async function createMission(params: CreateMissionParams) {
  const id = generateSnowflake();
  await db.insert(missions).values({
    id,
    tenantId: params.tenantId,
    creatorId: params.creatorId,
    goal: params.goal,
    priority: params.priority ?? 0,
    budgetCents: params.budgetCents,
    deadline: params.deadline,
  });
  return { id };
}

export async function getMission(id: bigint) {
  const rows = await db.select().from(missions).where(eq(missions.id, id));
  return rows[0] ?? null;
}

export async function listMissions(tenantId: bigint, status?: string) {
  const conditions = status
    ? and(eq(missions.tenantId, tenantId), eq(missions.status, status))
    : eq(missions.tenantId, tenantId);
  return db.select().from(missions).where(conditions);
}

export async function updateMissionStatus(id: bigint, status: string) {
  const completedAt = status === "completed" || status === "failed" || status === "cancelled" ? new Date() : undefined;
  await db
    .update(missions)
    .set({ status, updatedAt: new Date(), ...(completedAt ? { completedAt } : {}) })
    .where(eq(missions.id, id));
}

export interface CreateTaskParams {
  missionId: bigint;
  parentTaskId?: bigint;
  description: string;
  priority?: number;
  requirements?: Record<string, unknown>;
}

export async function createTask(params: CreateTaskParams) {
  const id = generateSnowflake();
  await db.insert(tasks).values({
    id,
    missionId: params.missionId,
    parentTaskId: params.parentTaskId,
    description: params.description,
    priority: params.priority ?? 0,
    requirements: params.requirements ?? {},
  });
  return { id };
}

export async function listTasksByMission(missionId: bigint) {
  return db.select().from(tasks).where(eq(tasks.missionId, missionId));
}

export async function updateTaskStatus(id: bigint, status: string) {
  await db.update(tasks).set({ status, updatedAt: new Date() }).where(eq(tasks.id, id));
}

export interface CheckoutTaskParams {
  taskId: bigint;
  workerId: string;
  leaseSec?: number;
}

/**
 * Atomic checkout — INSERT vào assignments dựa vào unique partial index để
 * đảm bảo chỉ 1 worker checkout thành công cho mỗi task tại 1 thời điểm; nếu
 * đã có assignment 'leased' khác, INSERT sẽ vi phạm constraint và fail (caller
 * bắt lỗi unique violation, coi là "đã bị worker khác lease").
 */
export async function checkoutTask(params: CheckoutTaskParams) {
  const id = generateSnowflake();
  const leaseUntil = new Date(Date.now() + (params.leaseSec ?? 300) * 1000);
  try {
    await db.insert(assignments).values({
      id,
      taskId: params.taskId,
      workerId: params.workerId,
      leaseUntil,
    });
    await updateTaskStatus(params.taskId, "assigned");
    return { success: true, assignmentId: id, leaseUntil };
  } catch (err) {
    // Unique violation trên idx_control_plane_assignments_task_active_lease
    // -> task đã được worker khác lease, đây KHÔNG phải lỗi bất ngờ.
    return { success: false, reason: "task_already_leased" };
  }
}

export async function releaseAssignment(assignmentId: bigint, status: "completed" | "failed" | "released") {
  await db.update(assignments).set({ status, updatedAt: new Date() }).where(eq(assignments.id, assignmentId));
}
