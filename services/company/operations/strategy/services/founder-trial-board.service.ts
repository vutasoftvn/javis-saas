import { and, desc, eq, isNull } from "drizzle-orm";
import { db } from "../../models/db";
import { twelveWeekCycles, cycleReviews } from "../../../shared/db/schema/operations";
import { evidence } from "../../../shared/db/schema/strategy";
import { TenantContext } from "../../../shared/types/tenant_context";
import { getProjectInWorkspace } from "../../services/project-access.service";
import { getRankedAssumptionsByProjectInWorkspace } from "./assumption.service";
import { listExperimentsInWorkspace } from "./experiment-proposal.service";
import { listDecisionRecordsInWorkspace } from "./decision-recording.service";

// Founder Trial Board (Founder Trial R1 — spec §4). Read model thuần, KHÔNG bảng
// mới: ghép Operating Cycle + Assumptions (hypothesis) + Experiments (test
// contract) + Evidence + Founder Decision từ các bảng đã tồn tại.

export interface FounderTrialCycleView {
  cycleId: string | null;
  durationWeeks: number | null;
  // Optimistic-lock revision của Operating Cycle. Flutter phải gửi lại giá trị
  // này (`expectedRevision`) khi resize; null khi project chưa có cycle.
  revision: number | null;
  currentWeek: number | null;
  stageAtStart: string | null;
  calendarState: string | null;
  startLocalDate: string | null;
  timezone: string | null;
  reviews: Array<{
    id: string;
    kind: string;
    scheduledWeekNo: number;
    scheduledAt: string | null;
    status: string;
  }>;
}

type CycleRow = typeof twelveWeekCycles.$inferSelect;
type ReviewRow = typeof cycleReviews.$inferSelect;

// Dựng FounderTrialCycleView từ 1 cycle row + review rows đã lọc
// (cycleId + workspaceId + deletedAt). Dùng chung bởi Board read model và
// lệnh resize để tránh drift shape.
export function buildFounderTrialCycleView(
  cycleRow: CycleRow | null | undefined,
  reviewRows: ReviewRow[]
): FounderTrialCycleView {
  return {
    cycleId: cycleRow ? cycleRow.id.toString() : null,
    durationWeeks: cycleRow?.durationWeeks ?? null,
    revision: cycleRow?.revision ?? null,
    currentWeek: cycleRow?.currentWeek ?? null,
    stageAtStart: cycleRow?.stageAtStart ?? null,
    calendarState: cycleRow?.calendarState ?? null,
    startLocalDate: cycleRow?.startLocalDate ? String(cycleRow.startLocalDate) : null,
    timezone: cycleRow?.timezone ?? null,
    reviews: reviewRows
      .map((r) => ({
        id: r.id.toString(),
        kind: r.kind,
        scheduledWeekNo: r.scheduledWeekNo,
        scheduledAt: r.scheduledAt ? r.scheduledAt.toISOString() : null,
        status: r.status,
      }))
      .sort((a, b) => a.scheduledWeekNo - b.scheduledWeekNo),
  };
}

export interface FounderTrialAssumptionView {
  id: string;
  statement: string;
  importance: number;
  uncertainty: number;
  riskScore: number;
  status: string;
  rank: number;
  isFocus: boolean; // nằm trong top 1-3 assumption chưa kiểm chứng
}

export interface FounderTrialExperimentView {
  id: string;
  assumptionId: string | null;
  hypothesis: string;
  method: string;
  successCriteria: string;
  status: string;
  linkedToAssumption: boolean;
}

export interface FounderTrialEvidenceView {
  id: string;
  claim: string;
  status: string; // candidate | approved | rejected
  supportsOrRefutes: string;
  sourceType: string;
  experimentId: string | null;
  linkedToExperiment: boolean;
  // True chỉ khi evidence gắn với một experiment thuộc project VÀ experiment đó
  // gắn một assumption cũng thuộc project (same-project experiment→assumption
  // join). Đây là điều kiện DUY NHẤT để evidence đóng góp vào readiness coverage
  // của Founder Brief — evidence trực tiếp / experiment generic không được tính.
  linkedToFounderTrialAssumption: boolean;
  observedAt: string | null;
}

export interface FounderTrialDecisionView {
  id: string;
  decision: string; // proceed | pivot | kill | hold
  createdAt: string;
}

export interface FounderTrialBoardView {
  projectId: string;
  cycle: FounderTrialCycleView;
  assumptions: FounderTrialAssumptionView[];
  experiments: FounderTrialExperimentView[];
  evidence: {
    candidate: FounderTrialEvidenceView[];
    approved: FounderTrialEvidenceView[];
    rejected: FounderTrialEvidenceView[];
    // Evidence chưa gắn experiment: hiển thị nhưng NẰM NGOÀI kết luận readiness.
    unlinked: FounderTrialEvidenceView[];
  };
  decisions: FounderTrialDecisionView[];
}

const FOCUS_ASSUMPTION_LIMIT = 3;
const UNTESTED_STATUSES = new Set(["untested", "testing", "in_progress"]);

export async function getFounderTrialBoard(
  ctx: TenantContext,
  projectId: string
): Promise<FounderTrialBoardView> {
  // Xác nhận project thuộc workspace của caller trước mọi read.
  await getProjectInWorkspace(projectId, ctx);

  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);

  const [cycleRow] = await db
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

  const reviewRows = cycleRow
    ? await db
        .select()
        .from(cycleReviews)
        .where(eq(cycleReviews.cycleId, cycleRow.id))
    : [];

  const cycle: FounderTrialCycleView = buildFounderTrialCycleView(cycleRow, reviewRows);

  const { items: ranked } = await getRankedAssumptionsByProjectInWorkspace(ctx, projectId);
  let focusCount = 0;
  const assumptions: FounderTrialAssumptionView[] = ranked.map((a) => {
    const untested = UNTESTED_STATUSES.has(a.status ?? "untested");
    const isFocus = untested && focusCount < FOCUS_ASSUMPTION_LIMIT;
    if (isFocus) focusCount += 1;
    return {
      id: a.id.toString(),
      statement: a.statement,
      importance: a.importance,
      uncertainty: a.uncertainty,
      riskScore: a.computedRiskScore,
      status: a.status ?? "untested",
      rank: a.rank,
      isFocus,
    };
  });

  const projectAssumptionIds = new Set(assumptions.map((a) => a.id));

  const { items: experimentItems } = await listExperimentsInWorkspace(ctx, { projectId });
  const experiments: FounderTrialExperimentView[] = experimentItems.map((e) => ({
    id: e.id,
    assumptionId: e.assumptionId,
    hypothesis: e.hypothesis,
    method: e.method,
    successCriteria: e.successCriteria,
    status: e.status,
    linkedToAssumption: e.assumptionId != null,
  }));

  // Experiment "Founder-Trial hợp lệ" = có assumptionId trỏ tới một assumption
  // của CHÍNH project này. Chỉ evidence gắn experiment trong tập này mới đóng góp
  // vào readiness coverage.
  const founderTrialExperimentIds = new Set(
    experiments
      .filter((e) => e.assumptionId != null && projectAssumptionIds.has(e.assumptionId))
      .map((e) => e.id)
  );

  const evidenceRows = await db
    .select()
    .from(evidence)
    .where(
      and(
        eq(evidence.projectId, pId),
        eq(evidence.workspaceId, wsId),
        isNull(evidence.deletedAt)
      )
    );

  const toEvidenceView = (r: typeof evidenceRows[number]): FounderTrialEvidenceView => {
    const experimentId = r.experimentId ? r.experimentId.toString() : null;
    return {
      id: r.id.toString(),
      claim: r.claim,
      status: r.status,
      supportsOrRefutes: r.supportsOrRefutes,
      sourceType: r.sourceType,
      experimentId,
      linkedToExperiment: experimentId != null,
      linkedToFounderTrialAssumption:
        experimentId != null && founderTrialExperimentIds.has(experimentId),
      observedAt: r.observedAt ? r.observedAt.toISOString() : null,
    };
  };

  const evidenceViews = evidenceRows.map(toEvidenceView);
  const evidenceGroups = {
    candidate: evidenceViews.filter((e) => e.status === "candidate"),
    approved: evidenceViews.filter((e) => e.status === "approved"),
    rejected: evidenceViews.filter((e) => e.status === "rejected"),
    unlinked: evidenceViews.filter((e) => !e.linkedToExperiment),
  };

  const { items: decisionItems } = await listDecisionRecordsInWorkspace(ctx, { projectId });
  const decisions: FounderTrialDecisionView[] = decisionItems.map((d) => ({
    id: d.id,
    decision: d.decision,
    createdAt: d.createdAt,
  }));

  return {
    projectId,
    cycle,
    assumptions,
    experiments,
    evidence: evidenceGroups,
    decisions,
  };
}
