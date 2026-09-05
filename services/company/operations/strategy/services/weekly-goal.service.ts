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
import {
  getLocalDateFromInstant,
  nextMondayOnOrAfterLocalDate,
  calculateCycleEndDateExclusive,
  resolveExecutionWeek,
} from "../../services/execution-calendar";

export interface SetWeeklyGoalParams {
  projectId: string;
  workspaceId: string;
  cycleId?: string;
  weekNo?: number;
  expectedVersion?: number;
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
 * Ghi "mục tiêu tuần" của founder vào weekly_plans.
 * Khi cycleId và weekNo được cung cấp, ghi đúng vào tuần đó.
 * Khi không cung cấp cycleId, chỉ tự suy ra nếu tồn tại đúng 1 chu kỳ ACTIVE READY.
 * Nếu có nhiều chu kỳ ACTIVE, bắt buộc người dùng chỉ định rõ cycleId.
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

    let targetCycle: typeof twelveWeekCycles.$inferSelect | null = null;
    let targetWeekNo = params.weekNo ?? 1;

    if (params.cycleId) {
      const [cycle] = await tx
        .select()
        .from(twelveWeekCycles)
        .where(
          and(
            eq(twelveWeekCycles.id, BigInt(params.cycleId)),
            eq(twelveWeekCycles.projectId, pId),
            eq(twelveWeekCycles.workspaceId, wsId),
            isNull(twelveWeekCycles.deletedAt)
          )
        )
        .limit(1);

      if (!cycle) throw APIError.notFound(`cycle ${params.cycleId} not found`);
      targetCycle = cycle;
    } else {
      const activeCycles = await tx
        .select()
        .from(twelveWeekCycles)
        .where(
          and(
            eq(twelveWeekCycles.projectId, pId),
            eq(twelveWeekCycles.workspaceId, wsId),
            eq(twelveWeekCycles.status, "ACTIVE"),
            isNull(twelveWeekCycles.deletedAt)
          )
        );

      const readyCycles = activeCycles.filter(
        (c) => c.calendarState === "READY" || c.calendarState === null
      );

      if (readyCycles.length > 1) {
        throw APIError.failedPrecondition(
          "Multiple active execution cycles found. Explicit cycleId is required."
        );
      } else if (readyCycles.length === 1) {
        targetCycle = readyCycles[0]!;
        if (!params.weekNo && targetCycle.startLocalDate) {
          const todayLocal = getLocalDateFromInstant(new Date(), targetCycle.timezone || "UTC");
          const resolved = resolveExecutionWeek(
            String(targetCycle.startLocalDate),
            targetCycle.durationWeeks,
            todayLocal
          );
          if (resolved !== null) {
            targetWeekNo = resolved;
          }
        }
      } else {
        // No active ready cycle, check if any cycle exists
        if (activeCycles.length === 1) {
          targetCycle = activeCycles[0]!;
        } else if (activeCycles.length > 1) {
          throw APIError.failedPrecondition(
            "Multiple active execution cycles found. Explicit cycleId is required."
          );
        } else {
          // Create default cycle
          const todayLocal = getLocalDateFromInstant(new Date(), "UTC");
          const startLocalDate = nextMondayOnOrAfterLocalDate(todayLocal);
          const endLocalDateExclusive = calculateCycleEndDateExclusive(startLocalDate, 2);

          const [created] = await tx
            .insert(twelveWeekCycles)
            .values({
              id: generateSnowflake(),
              workspaceId: wsId,
              projectId: pId,
              stageAtStart: "P0_DISCOVERY",
              durationWeeks: 2,
              timezone: "UTC",
              startLocalDate: startLocalDate || null,
              endLocalDateExclusive: endLocalDateExclusive || null,
              calendarState: "READY",
              revision: 1,
            })
            .returning();
          targetCycle = created!;
        }
      }
    }

    if (targetWeekNo < 1 || targetWeekNo > targetCycle.durationWeeks) {
      throw APIError.invalidArgument(
        `weekNo ${targetWeekNo} is outside cycle duration of ${targetCycle.durationWeeks} weeks`
      );
    }

    if (params.expectedVersion !== undefined && targetCycle.revision !== params.expectedVersion) {
      throw APIError.failedPrecondition(
        `Cycle revision conflict: expected ${params.expectedVersion}, actual ${targetCycle.revision}`
      );
    }

    const [plan] = await tx
      .insert(weeklyPlans)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        cycleId: targetCycle.id,
        weekNo: targetWeekNo,
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
