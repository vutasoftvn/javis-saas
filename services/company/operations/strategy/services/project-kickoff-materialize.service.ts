import { and, desc, eq, isNull } from "drizzle-orm";
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
import { insertContractRevision } from "../../services/task-outcome-contract.service";
import type { FirstWeekAction, BasicKickoffStage } from "./project-operating-setup.service";
import {
  calculateCycleEndDateExclusive,
  getLocalDateFromInstant,
} from "../../services/execution-calendar";

export interface MaterializeFirstWeekPlanParams {
  projectId: string;
  previousActions: FirstWeekAction[];
  actions: FirstWeekAction[];
  firstWeekOutcome: string | null;
  selectedStage: BasicKickoffStage | null;
  stageDurationWeeks: number | null;
  cycleDurationWeeks?: number | null;
  cycleId?: string | null;
  roundStartDate: Date | null;
}

type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];

/**
 * Nối first-week actions của Project Kickoff vào dữ liệu thực thi thật:
 * operating.twelve_week_cycles → operating.weekly_plans (tuần 1) →
 * operating.weekly_commitments (không OKR) → operating.tasks.
 * Diff theo `id` ổn định của action (source_action_id):
 * - Thêm mới: tạo task + commitment với source_revision=1, revision=1.
 * - Sửa: nếu task draft/todo thì cập nhật title, increment revision; nếu đã done/in_progress thì giữ nguyên lịch sử.
 * - Xoá: nếu task draft/todo thì cancel/soft-delete; nếu đã done thì giữ nguyên lịch sử và bằng chứng.
 * Phải chạy trong transaction chung với việc ghi project_operating_setups.
 */
export async function materializeFirstWeekPlan(
  tx: Tx,
  ctx: TenantContext,
  params: MaterializeFirstWeekPlanParams
): Promise<void> {
  const {
    projectId,
    previousActions,
    actions,
    firstWeekOutcome,
    selectedStage,
    stageDurationWeeks,
    cycleDurationWeeks,
    cycleId,
    roundStartDate,
  } = params;

  if (actions.length === 0 && previousActions.length === 0) {
    return;
  }

  // Tuần 1 luôn kéo dài đúng 7 ngày kể từ mốc bắt đầu vòng
  const weekEndDate = roundStartDate
    ? new Date(roundStartDate.getTime() + 7 * 24 * 60 * 60 * 1000)
    : null;

  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);

  let cycle: typeof twelveWeekCycles.$inferSelect | undefined;

  if (cycleId) {
    const [c] = await tx
      .select()
      .from(twelveWeekCycles)
      .where(
        and(
          eq(twelveWeekCycles.id, BigInt(cycleId)),
          eq(twelveWeekCycles.workspaceId, wsId),
          isNull(twelveWeekCycles.deletedAt)
        )
      )
      .limit(1);
    cycle = c;
  }

  if (!cycle) {
    const [existing] = await tx
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
    cycle = existing;
  }

  const durationWeeks = cycleDurationWeeks ?? stageDurationWeeks ?? 2;

  if (!cycle) {
    let startLocalDate: string | null = null;
    let endLocalDateExclusive: string | null = null;
    let calendarState = "NEEDS_SETUP";

    if (roundStartDate) {
      startLocalDate = getLocalDateFromInstant(roundStartDate, "UTC");
      endLocalDateExclusive = calculateCycleEndDateExclusive(startLocalDate, durationWeeks);
      calendarState = "READY";
    }

    const [created] = await tx
      .insert(twelveWeekCycles)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: pId,
        stageAtStart: selectedStage ?? "P0_DISCOVERY",
        durationWeeks,
        startLocalDate: startLocalDate || null,
        endLocalDateExclusive: endLocalDateExclusive || null,
        calendarState,
        revision: 1,
      })
      .returning();
    cycle = created;
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
      startDate: roundStartDate,
      endDate: weekEndDate,
    })
    .onConflictDoUpdate({
      target: [weeklyPlans.cycleId, weeklyPlans.weekNo],
      set: {
        focus: firstWeekOutcome,
        mission: firstWeekOutcome,
        startDate: roundStartDate,
        endDate: weekEndDate,
        updatedAt: new Date(),
      },
    })
    .returning();

  const prevMap = new Map(previousActions.map((a) => [a.id, a]));
  const currMap = new Map(actions.map((a) => [a.id, a]));

  const added = actions.filter((a) => !prevMap.has(a.id));
  const removed = previousActions.filter((a) => !currMap.has(a.id));
  const changed = actions.filter((a) => prevMap.has(a.id) && prevMap.get(a.id)!.title !== a.title);

  // 1. Added actions
  for (const action of added) {
    const [commitment] = await tx
      .insert(weeklyCommitments)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        weeklyPlanId: plan!.id,
        initiativeId: null,
        title: action.title,
        sourceActionId: action.id,
        sourceRevision: 1,
        revision: 1,
      })
      .returning();

    const taskId = BigInt(action.id);

    await tx.insert(tasks).values({
      id: taskId,
      workspaceId: wsId,
      title: action.title,
      source: "project_kickoff",
      sourceActionId: action.id,
      sourceRevision: 1,
      revision: 1,
      weeklyCommitmentId: commitment!.id,
    });

    await tx
      .insert(taskProjects)
      .values({
        workspaceId: wsId,
        taskId,
        projectId: pId,
      })
      .onConflictDoNothing();

    // Task 1A: mỗi action tuần 1 nhận một Outcome Contract DRAFT type
    // VALIDATION riêng, expected outcome DẪN XUẤT từ action (không tái dùng
    // nguyên văn outcome của tuần/dự án — spec §6.1). Manager xác nhận qua
    // Task 2 mới chuyển CONFIRMED + QUEUED.
    await insertContractRevision(
      tx,
      {
        workspaceId: ctx.workspaceId,
        taskId: taskId.toString(),
        outcomeType: "VALIDATION",
        expectedOutcome: `Hoàn thành "${action.title}" với bằng chứng và một quyết định tiếp theo`,
        acceptanceCriteria: { action: action.title, decisionRecorded: true },
        expectedEvidenceRefs: [],
        impactHypothesis: firstWeekOutcome
          ? `Đóng góp vào kết quả tuần 1: ${firstWeekOutcome}`
          : `Bước kiểm chứng tuần 1 cho "${action.title}"`,
      },
      { status: "DRAFT", revision: 1 }
    );
  }

  // 2. Changed actions (update draft/todo tasks, preserve history for done/in_progress)
  for (const action of changed) {
    const taskId = BigInt(action.id);
    const [existingTask] = await tx
      .select({
        id: tasks.id,
        status: tasks.status,
        sourceRevision: tasks.sourceRevision,
        revision: tasks.revision,
        weeklyCommitmentId: tasks.weeklyCommitmentId,
      })
      .from(tasks)
      .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId)))
      .limit(1);

    if (existingTask) {
      if (existingTask.status === "todo" || existingTask.status === "draft") {
        const nextRev = (existingTask.revision ?? 1) + 1;
        const nextSourceRev = (existingTask.sourceRevision ?? 1) + 1;

        await tx
          .update(tasks)
          .set({
            title: action.title,
            sourceRevision: nextSourceRev,
            revision: nextRev,
            updatedAt: new Date(),
          })
          .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId)));

        if (existingTask.weeklyCommitmentId) {
          await tx
            .update(weeklyCommitments)
            .set({
              title: action.title,
              sourceRevision: nextSourceRev,
              revision: nextRev,
              updatedAt: new Date(),
            })
            .where(
              and(
                eq(weeklyCommitments.id, existingTask.weeklyCommitmentId),
                eq(weeklyCommitments.workspaceId, wsId)
              )
            );
        }
      }
      // If task is 'done' or 'in_progress', do not overwrite title, preserving historical completion!
    }
  }

  // 3. Removed actions (cancel todo/draft, preserve done tasks)
  for (const action of removed) {
    const taskId = BigInt(action.id);
    const now = new Date();

    const [existingTask] = await tx
      .select({ status: tasks.status, weeklyCommitmentId: tasks.weeklyCommitmentId })
      .from(tasks)
      .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId)))
      .limit(1);

    if (existingTask) {
      // If already done, do not delete or mark cancelled! Keep historical evidence intact.
      if (existingTask.status === "done") {
        continue;
      }

      await tx
        .update(tasks)
        .set({ deletedAt: now, status: "cancelled" })
        .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId)));

      if (existingTask.weeklyCommitmentId) {
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
}
