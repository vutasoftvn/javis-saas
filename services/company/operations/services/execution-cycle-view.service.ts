import { APIError } from "encore.dev/api";
import { and, desc, eq, inArray, isNull } from "drizzle-orm";
import { db } from "../models/db";
import {
  twelveWeekCycles,
  weeklyPlans,
  weeklyCommitments,
  cycleKeyResults,
  keyResults,
} from "../../shared/db/schema/operations";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  getLocalDateFromInstant,
  resolveExecutionWeek,
} from "./execution-calendar";
import {
  calculateExecutionScore,
  calculateOutcomeScore,
  computeLinearProgress,
} from "./execution-outcome.service";

export interface ExecutionCycleViewSummary {
  id: string;
  displayName: string | null;
  durationWeeks: number;
  startLocalDate: string | null;
  endLocalDateExclusive: string | null;
  timezone: string;
  revision: number;
  status: string;
}

export interface ExecutionCycleWeeklyPlanView {
  id: string;
  weekNo: number;
  startDate: string | null;
  endDate: string | null;
  focus: string | null;
  mission: string | null;
  executionScore: number | null;
  outcomeScore: number | null;
  reflection: string | null;
  decisionId: string | null;
}

export interface ExecutionCycleCommitmentView {
  id: string;
  weeklyPlanId: string;
  title: string;
  status: string;
  plannedEffort: string | null;
  commitmentOwnerType: string | null;
  ownerMemberId: string | null;
  purposeType: string;
  purposeRef: string | null;
  executionMode: string | null;
  decisionId: string | null;
  revision: number;
}

export interface ExecutionCycleLinkedKrView {
  id: string;
  title: string | null;
  targetValue: number | null;
  currentValue: number | null;
  unit: string | null;
  progress: number | null;
  status: string;
}

export interface ExecutionCycleViewResponse {
  cycle: ExecutionCycleViewSummary | null;
  currentWeek: number | null;
  weeklyPlans: ExecutionCycleWeeklyPlanView[];
  commitments: ExecutionCycleCommitmentView[];
  linkedKrs: ExecutionCycleLinkedKrView[];
  executionScore: number | null;
  outcomeProgress: number | null;
  dataIssues: string[];
  allowedActions: string[];
}

export interface GetExecutionCycleViewParams {
  projectId: string;
  cycleId?: string;
}

/**
 * Returns a consolidated, projection-consistent Execution Cycle View for the frontend.
 * Evaluates current execution week, weekly plans, commitments, linked KRs,
 * execution outcome score, and data health issues deterministically.
 */
export async function getExecutionCycleView(
  ctx: TenantContext,
  params: GetExecutionCycleViewParams
): Promise<ExecutionCycleViewResponse> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(params.projectId);
  const dataIssues: string[] = [];

  // 1. Locate cycle: by cycleId if provided, or the latest active cycle for the project
  let cycleRow: typeof twelveWeekCycles.$inferSelect | undefined;
  if (params.cycleId && params.cycleId.trim()) {
    const cycleIdBig = BigInt(params.cycleId);
    const [found] = await db
      .select()
      .from(twelveWeekCycles)
      .where(
        and(
          eq(twelveWeekCycles.id, cycleIdBig),
          eq(twelveWeekCycles.workspaceId, wsId),
          isNull(twelveWeekCycles.deletedAt)
        )
      )
      .limit(1);
    cycleRow = found;
  } else {
    const [latest] = await db
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
    cycleRow = latest;
  }

  if (!cycleRow) {
    return {
      cycle: null,
      currentWeek: null,
      weeklyPlans: [],
      commitments: [],
      linkedKrs: [],
      executionScore: null,
      outcomeProgress: null,
      dataIssues: ["No execution cycle found for this project"],
      allowedActions: ["cycle.create"],
    };
  }

  const cycleSummary: ExecutionCycleViewSummary = {
    id: cycleRow.id.toString(),
    displayName: cycleRow.displayName || cycleRow.theme || `Chu kỳ thực thi ${cycleRow.durationWeeks} tuần`,
    durationWeeks: cycleRow.durationWeeks,
    startLocalDate: cycleRow.startLocalDate ? String(cycleRow.startLocalDate) : null,
    endLocalDateExclusive: cycleRow.endLocalDateExclusive ? String(cycleRow.endLocalDateExclusive) : null,
    timezone: cycleRow.timezone || "UTC",
    revision: cycleRow.revision ?? 1,
    status: cycleRow.status,
  };

  // 2. Resolve current week from startLocalDate & timezone
  let currentWeek: number | null = null;
  if (cycleRow.startLocalDate) {
    const now = new Date();
    const todayLocal = getLocalDateFromInstant(now, cycleRow.timezone || "UTC");
    currentWeek = resolveExecutionWeek(String(cycleRow.startLocalDate), cycleRow.durationWeeks, todayLocal);
    if (currentWeek === null) {
      dataIssues.push("Current date is outside execution cycle window");
    }
  } else {
    dataIssues.push("Cycle start date is not configured (NEEDS_SETUP)");
  }

  // 3. Load weekly plans
  const planRows = await db
    .select()
    .from(weeklyPlans)
    .where(
      and(
        eq(weeklyPlans.cycleId, cycleRow.id),
        eq(weeklyPlans.workspaceId, wsId),
        isNull(weeklyPlans.deletedAt)
      )
    )
    .orderBy(weeklyPlans.weekNo);

  const weeklyPlansView: ExecutionCycleWeeklyPlanView[] = planRows.map((p) => ({
    id: p.id.toString(),
    weekNo: p.weekNo,
    startDate: p.startDate ? p.startDate.toISOString() : null,
    endDate: p.endDate ? p.endDate.toISOString() : null,
    focus: p.focus,
    mission: p.mission,
    executionScore: p.executionScore,
    outcomeScore: p.outcomeScore,
    reflection: p.reflection,
    decisionId: p.decisionId ? p.decisionId.toString() : null,
  }));

  // 4. Load commitments for these weekly plans
  let commitmentsView: ExecutionCycleCommitmentView[] = [];
  if (planRows.length > 0) {
    const planIds = planRows.map((p) => p.id);
    const commitmentRows = await db
      .select()
      .from(weeklyCommitments)
      .where(
        and(
          inArray(weeklyCommitments.weeklyPlanId, planIds),
          eq(weeklyCommitments.workspaceId, wsId),
          isNull(weeklyCommitments.deletedAt)
        )
      )
      .orderBy(weeklyCommitments.createdAt);

    commitmentsView = commitmentRows.map((c) => ({
      id: c.id.toString(),
      weeklyPlanId: c.weeklyPlanId.toString(),
      title: c.title,
      status: c.status,
      plannedEffort: c.plannedEffort,
      commitmentOwnerType: c.commitmentOwnerType,
      ownerMemberId: c.ownerMemberId ? c.ownerMemberId.toString() : null,
      purposeType: c.purposeType,
      purposeRef: c.purposeRef,
      executionMode: c.executionMode,
      decisionId: c.decisionId ? c.decisionId.toString() : null,
      revision: c.revision ?? 1,
    }));
  }

  // 5. Load linked Key Results via cycleKeyResults junction
  const linkedKrLinks = await db
    .select({
      keyResultId: cycleKeyResults.keyResultId,
    })
    .from(cycleKeyResults)
    .where(
      and(
        eq(cycleKeyResults.cycleId, cycleRow.id),
        eq(cycleKeyResults.workspaceId, wsId)
      )
    );

  let linkedKrsView: ExecutionCycleLinkedKrView[] = [];
  if (linkedKrLinks.length > 0) {
    const krIds = linkedKrLinks.map((l) => l.keyResultId);
    const krRows = await db
      .select()
      .from(keyResults)
      .where(
        and(
          inArray(keyResults.id, krIds),
          eq(keyResults.workspaceId, wsId),
          isNull(keyResults.deletedAt)
        )
      );

    linkedKrsView = krRows.map((kr) => {
      const progress = computeLinearProgress({
        baseline: kr.baselineValue,
        target: kr.targetValue,
        current: kr.currentValue,
      });
      return {
        id: kr.id.toString(),
        title: kr.title,
        targetValue: kr.targetValue,
        currentValue: kr.currentValue,
        unit: kr.unit,
        progress,
        status: kr.status,
      };
    });
  }

  // 6. Compute Execution Score: based on commitments of current week, or overall commitments if no current week
  let targetCommitments = commitmentsView;
  if (currentWeek !== null) {
    const currentPlan = planRows.find((p) => p.weekNo === currentWeek);
    if (currentPlan) {
      targetCommitments = commitmentsView.filter((c) => c.weeklyPlanId === currentPlan.id.toString());
    }
  }

  const executionScore = calculateExecutionScore(
    targetCommitments.map((c) => ({
      id: c.id,
      status: c.status,
      hasEligibleEvidence: true, // evaluated by outcome service
    }))
  );

  // 7. Compute Cycle Outcome Progress: average of valid linked KR progresses
  const outcomeProgress = calculateOutcomeScore(
    linkedKrsView.map((k) => ({
      id: k.id,
      score: k.progress,
    }))
  );

  const allowedActions = [
    "cycle.edit",
    "weekly.plan.edit",
    "commitment.create",
    "kr.link",
  ];

  return {
    cycle: cycleSummary,
    currentWeek,
    weeklyPlans: weeklyPlansView,
    commitments: commitmentsView,
    linkedKrs: linkedKrsView,
    executionScore,
    outcomeProgress,
    dataIssues,
    allowedActions,
  };
}
