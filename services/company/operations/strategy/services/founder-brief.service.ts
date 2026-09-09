import { TenantContext } from "../../../shared/types/tenant_context";
import { getFounderTrialBoard, FounderTrialBoardView } from "./founder-trial-board.service";
import { getBudgetSummary } from "../../../finance-legal/services/budget-summary.service";
import { getFinancialSnapshotsService } from "../../../finance-legal/services/financial-snapshot.service";

// Founder Brief (Founder Trial R1 — spec §4 / Node E). Read model project-scoped:
// 5 trục readiness tính TẤT ĐỊNH từ dữ liệu thật của Founder Trial Board +
// finance. R1 KHÔNG có recommendation do agent sinh — chỉ một gợi ý DRAFT tính
// bằng luật, ghi rõ non-authoritative. `DecisionRecord` chỉ tạo bởi command
// tường minh của founder.

export type ReadinessAxisKey =
  | "problem"
  | "solution"
  | "traction"
  | "economics"
  | "compliance";

export type ReadinessState =
  | "not_assessed"
  | "no_evidence"
  | "emerging"
  | "supported"
  | "tracking"
  | "configuration_required"
  | "unavailable";

export interface ReadinessAxis {
  axis: ReadinessAxisKey;
  state: ReadinessState;
  evidenceRefs: string[];
  knownGaps: string[];
  lastObservedAt: string | null;
}

export interface FounderBriefView {
  projectId: string;
  axes: ReadinessAxis[];
  // Gợi ý DRAFT, KHÔNG có thẩm quyền. Founder phải ra command riêng để ghi
  // DecisionRecord (proceed | pivot | kill | hold).
  suggestedDecision: {
    label: "proceed" | "pivot" | "kill" | "hold";
    rationale: string;
    isAuthoritative: false;
  };
  generatedFrom: "deterministic_rules";
}

function latest(dates: Array<string | null | undefined>): string | null {
  const valid = dates.filter((d): d is string => !!d).sort();
  return valid.length ? valid[valid.length - 1] : null;
}

function problemAxis(board: FounderTrialBoardView): ReadinessAxis {
  const approved = board.evidence.approved.filter((e) => e.linkedToExperiment);
  const focusUntested = board.assumptions.filter((a) => a.isFocus);
  const gaps: string[] = [];
  if (focusUntested.length > 0) {
    gaps.push(`${focusUntested.length} giả thuyết trọng tâm chưa kiểm chứng`);
  }
  if (approved.length === 0) {
    gaps.push("Chưa có evidence được duyệt liên kết hypothesis");
  }
  if (board.evidence.unlinked.length > 0) {
    gaps.push(
      `${board.evidence.unlinked.length} evidence chưa liên kết hypothesis (ngoài kết luận)`
    );
  }
  const state: ReadinessState =
    approved.length >= 3 ? "supported" : approved.length >= 1 ? "emerging" : "no_evidence";
  return {
    axis: "problem",
    state,
    evidenceRefs: approved.map((e) => e.id),
    knownGaps: gaps,
    lastObservedAt: latest(approved.map((e) => e.observedAt)),
  };
}

function solutionAxis(board: FounderTrialBoardView): ReadinessAxis {
  const experimentsWithAssumption = board.experiments.filter((e) => e.linkedToAssumption);
  const approvedIds = new Set(
    board.evidence.approved.filter((e) => e.linkedToExperiment).map((e) => e.experimentId)
  );
  const validated = experimentsWithAssumption.filter((e) => approvedIds.has(e.id));
  const gaps: string[] = [];
  if (experimentsWithAssumption.length === 0) {
    gaps.push("Chưa có experiment nào gắn giả thuyết");
  } else if (validated.length === 0) {
    gaps.push("Có experiment nhưng chưa có evidence được duyệt cho nó");
  }
  const state: ReadinessState =
    validated.length >= 2 ? "supported" : validated.length >= 1 ? "emerging" : "no_evidence";
  return {
    axis: "solution",
    state,
    evidenceRefs: validated.map((e) => e.id),
    knownGaps: gaps,
    lastObservedAt: null,
  };
}

function tractionAxis(board: FounderTrialBoardView): ReadinessAxis {
  // R1: traction chỉ đo được khi có evidence không phải interview (vd telemetry,
  // financial actuals) đã duyệt. Marketing/lead project-scoped sẽ nối ở R1.2.
  const tractionEvidence = board.evidence.approved.filter(
    (e) => e.sourceType !== "sales_crm" && e.sourceType !== "interview"
  );
  const state: ReadinessState = tractionEvidence.length > 0 ? "emerging" : "not_assessed";
  return {
    axis: "traction",
    state,
    evidenceRefs: tractionEvidence.map((e) => e.id),
    knownGaps:
      tractionEvidence.length === 0
        ? ["Chưa có tín hiệu traction đo được (telemetry/doanh thu) được duyệt"]
        : [],
    lastObservedAt: latest(tractionEvidence.map((e) => e.observedAt)),
  };
}

async function economicsAxis(
  ctx: TenantContext,
  projectId: string
): Promise<ReadinessAxis> {
  const gaps: string[] = [];
  let state: ReadinessState = "configuration_required";
  let lastObservedAt: string | null = null;

  try {
    const budget = await getBudgetSummary(ctx, projectId);
    if (budget.coverage === "COMPLETE") {
      state = "tracking";
      lastObservedAt = budget.asOf;
    } else {
      gaps.push("Chưa cấu hình budget envelope cho project");
    }
  } catch {
    state = "unavailable";
    gaps.push("Không đọc được budget summary");
  }

  try {
    const snapshots = await getFinancialSnapshotsService(BigInt(ctx.workspaceId));
    if (snapshots.length > 0) {
      if (state === "configuration_required") state = "tracking";
      lastObservedAt = latest([lastObservedAt, snapshots[0].snapshotDate ?? null]);
    } else {
      gaps.push("Chưa có cash snapshot ở mức workspace (workspace liquidity)");
    }
  } catch {
    gaps.push("Không đọc được cash snapshot");
  }

  return { axis: "economics", state, evidenceRefs: [], knownGaps: gaps, lastObservedAt };
}

function complianceAxis(): ReadinessAxis {
  return {
    axis: "compliance",
    state: "not_assessed",
    evidenceRefs: [],
    knownGaps: [
      "Đánh giá pháp lý/compliance không thuộc phạm vi Release 1 (Legal Guard là post-R1)",
    ],
    lastObservedAt: null,
  };
}

function deriveSuggestion(axes: ReadinessAxis[]): FounderBriefView["suggestedDecision"] {
  const problem = axes.find((a) => a.axis === "problem")!;
  const solution = axes.find((a) => a.axis === "solution")!;

  if (problem.state === "no_evidence" && solution.state === "no_evidence") {
    return {
      label: "proceed",
      rationale:
        "Chưa có evidence duyệt cho giả thuyết trọng tâm — đề xuất tiếp tục discovery trong chu kỳ hiện tại.",
      isAuthoritative: false,
    };
  }
  if (problem.state === "supported" && solution.state !== "supported") {
    return {
      label: "hold",
      rationale:
        "Vấn đề đã có bằng chứng ủng hộ nhưng giải pháp chưa được kiểm chứng — cân nhắc tập trung experiment giải pháp trước khi mở rộng.",
      isAuthoritative: false,
    };
  }
  if (problem.state === "supported" && solution.state === "supported") {
    return {
      label: "proceed",
      rationale:
        "Cả vấn đề và giải pháp đều có evidence duyệt — đủ cơ sở để founder cân nhắc advance phase.",
      isAuthoritative: false,
    };
  }
  return {
    label: "hold",
    rationale:
      "Evidence còn mỏng — thu thêm dữ liệu trước khi ra quyết định lớn.",
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
    suggestedDecision: deriveSuggestion(axes),
    generatedFrom: "deterministic_rules",
  };
}
