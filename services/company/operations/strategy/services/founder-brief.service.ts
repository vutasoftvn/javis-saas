import { TenantContext } from "../../../shared/types/tenant_context";
import { getFounderTrialBoard, FounderTrialBoardView } from "./founder-trial-board.service";
import { getBudgetSummary } from "../../../finance-legal/services/budget-summary.service";
import { getFinancialSnapshotsService } from "../../../finance-legal/services/financial-snapshot.service";

// Founder Brief (Founder Trial R1 — spec §4 / Node E). Read model project-scoped:
// 5 trục readiness tính TẤT ĐỊNH từ dữ liệu thật. R1 chỉ báo EVIDENCE COVERAGE,
// gaps, freshness và configuration state — KHÔNG phát verdict, KHÔNG đề xuất
// quyết định. `DecisionRecord` (proceed | pivot | kill | hold) chỉ do command
// tường minh của founder tạo.
//
// Attribution nghiêm ngặt: chỉ evidence đã DUYỆT và
// `linkedToFounderTrialAssumption === true` (experiment→assumption cùng project)
// mới đóng góp vào problem/solution coverage. Evidence trực tiếp / experiment
// generic hiển thị được nhưng NẰM NGOÀI coverage.

export type ReadinessAxisKey =
  | "problem"
  | "solution"
  | "traction"
  | "economics"
  | "compliance";

export type AxisState =
  | "NOT_ASSESSED"
  | "NO_EVIDENCE"
  | "EVIDENCE_PRESENT"
  | "CONFIGURATION_REQUIRED"
  | "UNAVAILABLE";

export interface ReadinessAxis {
  axis: ReadinessAxisKey;
  state: AxisState;
  evidenceRefs: string[];
  knownGaps: string[];
  lastObservedAt: string | null;
}

export interface EconomicsSubcomponent {
  state: AxisState;
  sourceTimestamp: string | null;
  gap: string | null;
}

export interface EconomicsAxis extends ReadinessAxis {
  axis: "economics";
  // Hai thành phần ĐỘC LẬP — không gộp thành một economics status.
  projectBudget: EconomicsSubcomponent;
  workspaceLiquidity: EconomicsSubcomponent;
}

export interface FounderBriefView {
  projectId: string;
  axes: ReadinessAxis[];
  // Gợi ý trọng tâm cho lần review kế — KHÔNG có thẩm quyền, KHÔNG phải đề xuất
  // quyết định. Chỉ nêu trục nào còn thiếu bằng chứng/cấu hình.
  nextReviewFocus: {
    axis: ReadinessAxisKey | null;
    note: string;
    isAuthoritative: false;
  };
  generatedFrom: "deterministic_rules";
}

function latest(dates: Array<string | null | undefined>): string | null {
  const valid = dates.filter((d): d is string => !!d).sort();
  return valid.length ? valid[valid.length - 1] : null;
}

function problemAxis(board: FounderTrialBoardView): ReadinessAxis {
  const approved = board.evidence.approved.filter(
    (e) => e.linkedToFounderTrialAssumption
  );
  const focusUntested = board.assumptions.filter((a) => a.isFocus);
  const gaps: string[] = [];
  if (focusUntested.length > 0) {
    gaps.push(`${focusUntested.length} giả thuyết trọng tâm chưa kiểm chứng`);
  }
  if (approved.length === 0) {
    gaps.push("Chưa có evidence duyệt liên kết assumption của project");
  }
  if (board.evidence.unlinked.length > 0) {
    gaps.push(
      `${board.evidence.unlinked.length} evidence chưa liên kết hypothesis (ngoài coverage)`
    );
  }
  return {
    axis: "problem",
    state: approved.length > 0 ? "EVIDENCE_PRESENT" : "NO_EVIDENCE",
    evidenceRefs: approved.map((e) => e.id),
    knownGaps: gaps,
    lastObservedAt: latest(approved.map((e) => e.observedAt)),
  };
}

function solutionAxis(board: FounderTrialBoardView): ReadinessAxis {
  // Chỉ experiment gắn assumption của project (linkedToAssumption) + có ít nhất
  // một evidence duyệt cũng thoả linkedToFounderTrialAssumption.
  const approvedByExperiment = new Set(
    board.evidence.approved
      .filter((e) => e.linkedToFounderTrialAssumption)
      .map((e) => e.experimentId)
  );
  const validated = board.experiments.filter(
    (e) => e.linkedToAssumption && approvedByExperiment.has(e.id)
  );
  const gaps: string[] = [];
  const experimentsWithAssumption = board.experiments.filter((e) => e.linkedToAssumption);
  if (experimentsWithAssumption.length === 0) {
    gaps.push("Chưa có experiment nào gắn assumption của project");
  } else if (validated.length === 0) {
    gaps.push("Có experiment nhưng chưa có evidence duyệt liên kết assumption");
  }
  return {
    axis: "solution",
    state: validated.length > 0 ? "EVIDENCE_PRESENT" : "NO_EVIDENCE",
    evidenceRefs: board.evidence.approved
      .filter((e) => e.linkedToFounderTrialAssumption && approvedByExperiment.has(e.experimentId))
      .map((e) => e.id),
    knownGaps: gaps,
    lastObservedAt: null,
  };
}

function tractionAxis(board: FounderTrialBoardView): ReadinessAxis {
  // R1: traction chỉ đo được khi có evidence đã duyệt KHÔNG phải interview/CRM
  // (vd telemetry, financial actuals). Marketing/lead project-scoped nối ở R1.2.
  const tractionEvidence = board.evidence.approved.filter(
    (e) => e.sourceType !== "sales_crm" && e.sourceType !== "interview"
  );
  return {
    axis: "traction",
    state: tractionEvidence.length > 0 ? "EVIDENCE_PRESENT" : "NOT_ASSESSED",
    evidenceRefs: tractionEvidence.map((e) => e.id),
    knownGaps:
      tractionEvidence.length === 0
        ? ["Chưa có tín hiệu traction đo được (telemetry/doanh thu) được duyệt"]
        : [],
    lastObservedAt: latest(tractionEvidence.map((e) => e.observedAt)),
  };
}

async function projectBudgetSubcomponent(
  ctx: TenantContext,
  projectId: string
): Promise<EconomicsSubcomponent> {
  try {
    const budget = await getBudgetSummary(ctx, projectId);
    if (budget.coverage === "COMPLETE") {
      return { state: "EVIDENCE_PRESENT", sourceTimestamp: budget.asOf, gap: null };
    }
    return {
      state: "CONFIGURATION_REQUIRED",
      sourceTimestamp: null,
      gap: "Chưa cấu hình project budget envelope",
    };
  } catch {
    return {
      state: "UNAVAILABLE",
      sourceTimestamp: null,
      gap: "Không đọc được budget summary",
    };
  }
}

async function workspaceLiquiditySubcomponent(
  ctx: TenantContext
): Promise<EconomicsSubcomponent> {
  try {
    const snapshots = await getFinancialSnapshotsService(BigInt(ctx.workspaceId));
    if (snapshots.length > 0) {
      return {
        state: "EVIDENCE_PRESENT",
        sourceTimestamp: snapshots[0].snapshotDate ?? null,
        gap: null,
      };
    }
    return {
      state: "CONFIGURATION_REQUIRED",
      sourceTimestamp: null,
      gap: "Chưa có cash snapshot ở mức workspace (CAS chưa active)",
    };
  } catch {
    return {
      state: "UNAVAILABLE",
      sourceTimestamp: null,
      gap: "Không đọc được cash snapshot",
    };
  }
}

async function economicsAxis(
  ctx: TenantContext,
  projectId: string
): Promise<EconomicsAxis> {
  const projectBudget = await projectBudgetSubcomponent(ctx, projectId);
  const workspaceLiquidity = await workspaceLiquiditySubcomponent(ctx);

  const subStates = [projectBudget.state, workspaceLiquidity.state];
  let state: AxisState;
  if (subStates.includes("UNAVAILABLE")) {
    state = "UNAVAILABLE";
  } else if (subStates.includes("EVIDENCE_PRESENT")) {
    state = "EVIDENCE_PRESENT";
  } else {
    state = "CONFIGURATION_REQUIRED";
  }

  return {
    axis: "economics",
    state,
    evidenceRefs: [],
    knownGaps: [projectBudget.gap, workspaceLiquidity.gap].filter(
      (g): g is string => !!g
    ),
    lastObservedAt: latest([
      projectBudget.sourceTimestamp,
      workspaceLiquidity.sourceTimestamp,
    ]),
    projectBudget,
    workspaceLiquidity,
  };
}

function complianceAxis(): ReadinessAxis {
  return {
    axis: "compliance",
    state: "NOT_ASSESSED",
    evidenceRefs: [],
    knownGaps: [
      "Đánh giá pháp lý/compliance không thuộc phạm vi Release 1 (Legal Guard là post-R1)",
    ],
    lastObservedAt: null,
  };
}

// Non-authoritative: trục đầu tiên (problem → solution → traction → economics)
// còn thiếu bằng chứng/cấu hình. KHÔNG map sang proceed/pivot/kill/hold.
function deriveNextReviewFocus(
  axes: ReadinessAxis[]
): FounderBriefView["nextReviewFocus"] {
  const order: ReadinessAxisKey[] = ["problem", "solution", "traction", "economics"];
  for (const key of order) {
    const axis = axes.find((a) => a.axis === key)!;
    if (axis.state === "NO_EVIDENCE") {
      return {
        axis: key,
        note: `Trục "${key}" chưa có evidence duyệt liên kết — ưu tiên thu thập ở review kế.`,
        isAuthoritative: false,
      };
    }
    if (axis.state === "CONFIGURATION_REQUIRED") {
      return {
        axis: key,
        note: `Trục "${key}" cần cấu hình (budget/CAS) trước khi đọc được số liệu.`,
        isAuthoritative: false,
      };
    }
  }
  return {
    axis: null,
    note: "Không còn lỗ hổng evidence bắt buộc; founder tự chọn trọng tâm review.",
    isAuthoritative: false,
  };
}

export async function getFounderBrief(
  ctx: TenantContext,
  projectId: string
): Promise<FounderBriefView> {
  const board = await getFounderTrialBoard(ctx, projectId);
  const axes: ReadinessAxis[] = [
    problemAxis(board),
    solutionAxis(board),
    tractionAxis(board),
    await economicsAxis(ctx, projectId),
    complianceAxis(),
  ];
  return {
    projectId,
    axes,
    nextReviewFocus: deriveNextReviewFocus(axes),
    generatedFrom: "deterministic_rules",
  };
}
