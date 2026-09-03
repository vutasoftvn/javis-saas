import { and, desc, eq } from "drizzle-orm";
import { db } from "../../models/db";
import {
  twelveWeekCycles,
  weeklyPlans,
  weeklyCommitments,
  tasks,
  taskProjects,
} from "../../../shared/db/schema/operations";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { FirstWeekAction, BasicKickoffStage } from "./project-operating-setup.service";

export interface MaterializeFirstWeekPlanParams {
  projectId: string;
  previousActions: FirstWeekAction[];
  actions: FirstWeekAction[];
  firstWeekOutcome: string | null;
  selectedStage: BasicKickoffStage | null;
  stageDurationWeeks: number | null;
}

type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];

/**
 * Nối first-week actions của Project Kickoff vào dữ liệu thực thi thật:
 * operating.twelve_week_cycles → operating.weekly_plans (tuần 1) →
 * operating.weekly_commitments (không OKR) → operating.tasks.
 * Diff theo `id` ổn định của action (tái dùng làm tasks.id luôn) — action
 * mới xuất hiện thì tạo task, action biến mất thì soft-delete task+commitment.
 * Phải chạy trong transaction chung với việc ghi project_operating_setups.
 */
export async function materializeFirstWeekPlan(
  tx: Tx,
  ctx: TenantContext,
  params: MaterializeFirstWeekPlanParams
): Promise<void> {
  const { projectId, previousActions, actions, firstWeekOutcome, selectedStage, stageDurationWeeks } = params;

  if (actions.length === 0 && previousActions.length === 0) {
    return;
  }

  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);

  let [cycle] = await tx
    .select()
    .from(twelveWeekCycles)
    .where(and(eq(twelveWeekCycles.projectId, pId), eq(twelveWeekCycles.workspaceId, wsId)))
    .orderBy(desc(twelveWeekCycles.createdAt))
    .limit(1);

  if (!cycle) {
    [cycle] = await tx
      .insert(twelveWeekCycles)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: pId,
        stageAtStart: selectedStage ?? "P0_DISCOVERY",
        durationWeeks: stageDurationWeeks ?? 2,
      })
      .returning();
  }

  const [plan] = await tx
    .insert(weeklyPlans)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      cycleId: cycle!.id,
      weekNo: 1,
      focus: firstWeekOutcome,
      mission: firstWeekOutcome,
    })
    .onConflictDoUpdate({
      target: [weeklyPlans.cycleId, weeklyPlans.weekNo],
      set: {
        focus: firstWeekOutcome,
        mission: firstWeekOutcome,
        updatedAt: new Date(),
      },
    })
    .returning();

  const previousIds = new Set(previousActions.map((a) => a.id));
  const newIds = new Set(actions.map((a) => a.id));

  const added = actions.filter((a) => !previousIds.has(a.id));
  const removed = previousActions.filter((a) => !newIds.has(a.id));

  for (const action of added) {
    const [commitment] = await tx
      .insert(weeklyCommitments)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        weeklyPlanId: plan!.id,
        initiativeId: null,
        title: action.title,
      })
      .returning();

    const taskId = BigInt(action.id);

    await tx
      .insert(tasks)
      .values({
        id: taskId,
        workspaceId: wsId,
        title: action.title,
        source: "project_kickoff",
        weeklyCommitmentId: commitment!.id,
      })
      .onConflictDoUpdate({
        target: tasks.id,
        set: {
          title: action.title,
          weeklyCommitmentId: commitment!.id,
          updatedAt: new Date(),
        },
      });

    await tx
      .insert(taskProjects)
      .values({
        workspaceId: wsId,
        taskId,
        projectId: pId,
      })
      .onConflictDoNothing();
  }

  for (const action of removed) {
    const taskId = BigInt(action.id);
    const now = new Date();

    const [existingTask] = await tx
      .select({ weeklyCommitmentId: tasks.weeklyCommitmentId })
      .from(tasks)
      .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId)))
      .limit(1);

    await tx
      .update(tasks)
      .set({ deletedAt: now, status: "cancelled" })
      .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId)));

    if (existingTask?.weeklyCommitmentId) {
      await tx
        .update(weeklyCommitments)
        .set({ deletedAt: now })
        .where(
          and(
            eq(weeklyCommitments.id, existingTask.weeklyCommitmentId),
            eq(weeklyCommitments.workspaceId, wsId)
          )
        );
    }
  }
}
