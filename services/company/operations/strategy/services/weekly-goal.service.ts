import { randomUUID } from "node:crypto";
import { and, desc, eq, isNull } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../../models/db";
import {
  projects,
  twelveWeekCycles,
  weeklyPlans,
} from "../../../shared/db/schema/operations";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../../shared/events/envelope";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { WEEKLY_GOAL_SET } from "../../../shared/events";

export interface SetWeeklyGoalParams {
  projectId: string;
  workspaceId: string;
  focus: string;
  mission?: string | null;
  triggerDecomposition: boolean;
  origin: "command_center" | "chat";
  originRef?: string | null;
}

export interface SetWeeklyGoalResult {
  weeklyPlanId: string;
  focus: string;
  decompositionRequested: boolean;
}

/**
 * Ghi "mục tiêu tuần" của founder vào weekly_plans (tuần 1) — tái dùng chuỗi
 * 12WY (twelve_week_cycles → weekly_plans). Tạo lười cycle + plan lần đầu, các
 * lần sau chỉ cập nhật focus/mission. Khi triggerDecomposition=true, phát event
 * operating.weekly_goal.set.v1 cho apps/cosa chạy run phân rã.
 */
export async function setWeeklyGoalService(
  params: SetWeeklyGoalParams,
  authorization: string | undefined
): Promise<SetWeeklyGoalResult> {
  const ctx = await requireWorkspaceAccess(authorization, params.workspaceId);

  const focus = params.focus?.trim();
  if (!focus) throw APIError.invalidArgument("focus không được rỗng");

  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(params.projectId);
  const mission = params.mission?.trim() || focus;

  return await db.transaction(async (tx) => {
    const [proj] = await tx
      .select({ id: projects.id })
      .from(projects)
      .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)))
      .limit(1);
    if (!proj) throw APIError.notFound(`project ${params.projectId} not found`);

    let [cycle] = await tx
      .select()
      .from(twelveWeekCycles)
      .where(
        and(
          eq(twelveWeekCycles.projectId, pId),
          eq(twelveWeekCycles.workspaceId, wsId),
          isNull(twelveWeekCycles.deletedAt)
        )
      )
      .orderBy(desc(twelveWeekCycles.createdAt))
      .limit(1);

    if (!cycle) {
      [cycle] = await tx
        .insert(twelveWeekCycles)
        .values({
          id: generateSnowflake(),
          workspaceId: wsId,
          projectId: pId,
          stageAtStart: "P0_DISCOVERY",
          durationWeeks: 2,
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
        focus,
        mission,
      })
      .onConflictDoUpdate({
        target: [weeklyPlans.cycleId, weeklyPlans.weekNo],
        set: { focus, mission, updatedAt: new Date() },
      })
      .returning();

    const weeklyPlanId = plan!.id.toString();

    if (params.triggerDecomposition) {
      const event = makeBusinessEvent({
        eventType: WEEKLY_GOAL_SET,
        workspaceId: ctx.workspaceId,
        aggregateType: "weekly_plan",
        aggregateId: weeklyPlanId,
        correlationId: randomUUID(),
        actor: { kind: "user", id: ctx.userId || "0" },
        classification: "internal",
        payload: {
          workspaceId: ctx.workspaceId,
          projectId: params.projectId,
          weeklyPlanId,
          focus,
          origin: params.origin,
          originRef: params.originRef ?? null,
        },
      });
      await appendOutboxEvent(tx, event);
    }

    return {
      weeklyPlanId,
      focus,
      decompositionRequested: params.triggerDecomposition,
    };
  });
}
