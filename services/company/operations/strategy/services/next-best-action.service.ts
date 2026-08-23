export type ActionSource = "assumption" | "task" | "okr_gap" | "evidence" | "gate";

export interface AssumptionCandidateInput {
  id: number | bigint | string;
  statement: string;
  importance: number;
  uncertainty: number;
  riskScore?: number;
  status?: string;
}

export interface BlockedTaskCandidateInput {
  id: number | bigint | string;
  title: string;
  priority: "low" | "medium" | "high" | "urgent" | string;
  status: string;
}

export interface OkrGapCandidateInput {
  id: number | bigint | string;
  title: string;
  currentValue: number;
  targetValue: number;
  gapPercentage: number; // 0 - 100
}

export interface GateRequirementCandidateInput {
  stageKey: string;
  missingRequirement: string;
}

export interface NextActionInput {
  projectId: number | bigint | string;
  currentStage?: string;
  untestedAssumptions?: AssumptionCandidateInput[];
  blockedTasks?: BlockedTaskCandidateInput[];
  okrGaps?: OkrGapCandidateInput[];
  missingGateRequirements?: GateRequirementCandidateInput[];
}

export interface ActionCandidate {
  id?: number | bigint | string;
  source: ActionSource;
  score: number; // deterministic score 0 - 100
  rationale: string;
  title: string;
  metadata?: Record<string, any>;
}

export interface RankedAction {
  rank: number;
  candidate: ActionCandidate;
  llmRerankNote?: string | null;
}

/**
 * Sinh và xếp hạng Next Best Action hoàn toàn tất định (Deterministic).
 * Ràng buộc cứng: LLM chỉ được dùng để rerank sau đó ở agent layer, KHÔNG được tự sinh candidate hoặc tự đặt priority.
 */
export function generateAndRankNextActions(input: NextActionInput): RankedAction[] {
  const candidates: ActionCandidate[] = [];

  // 1. Nguồn từ Assumptions có rủi ro cao chưa kiểm chứng (weight score: max 100)
  for (const assumption of input.untestedAssumptions || []) {
    if (assumption.status === "validated" || assumption.status === "invalidated") continue;
    const importance = Math.max(1, Math.min(10, assumption.importance || 1));
    const uncertainty = Math.max(1, Math.min(10, assumption.uncertainty || 1));
    // Risk score = importance * uncertainty (1..100)
    const rawScore = importance * uncertainty;
    // Scale to base action score 50 - 95
    const score = Math.round(50 + (rawScore / 100) * 45);

    candidates.push({
      source: "assumption",
      score,
      title: `Validate critical assumption: "${assumption.statement}"`,
      rationale: `High-risk assumption with importance=${importance}, uncertainty=${uncertainty} (risk score: ${rawScore}). Design and execute an experiment immediately.`,
      metadata: { assumptionId: assumption.id, riskScore: rawScore },
    });
  }

  // 2. Nguồn từ Tasks bị Block (urgent/high priority blocked tasks: score 70 - 90)
  for (const task of input.blockedTasks || []) {
    let priorityWeight = 70;
    if (task.priority === "urgent") priorityWeight = 90;
    else if (task.priority === "high") priorityWeight = 80;
    else if (task.priority === "medium") priorityWeight = 70;
    else priorityWeight = 60;

    candidates.push({
      source: "task",
      score: priorityWeight,
      title: `Unblock critical task: "${task.title}"`,
      rationale: `Task is blocked with priority ${task.priority}. Resolving blockers restores operational momentum.`,
      metadata: { taskId: task.id, priority: task.priority },
    });
  }

  // 3. Nguồn từ OKR Gaps (khoảng cách lớn giữa target và current: score 60 - 85)
  for (const okr of input.okrGaps || []) {
    const gap = Math.max(0, Math.min(100, okr.gapPercentage));
    const score = Math.round(55 + (gap / 100) * 30);

    candidates.push({
      source: "okr_gap",
      score,
      title: `Close key result gap: "${okr.title}" (${gap}% remaining)`,
      rationale: `Key result has a ${gap}% progress gap toward target. Execute initiatives targeting this metric.`,
      metadata: { okrId: okr.id, gapPercentage: gap },
    });
  }

  // 4. Nguồn từ Gate requirements còn thiếu (score 65 - 80)
  for (const gateReq of input.missingGateRequirements || []) {
    candidates.push({
      source: "gate",
      score: 75,
      title: `Fulfill stage ${gateReq.stageKey} gate requirement: "${gateReq.missingRequirement}"`,
      rationale: `Stage transition is pending this requirement. Fulfilling it allows the project to advance.`,
      metadata: { stageKey: gateReq.stageKey, requirement: gateReq.missingRequirement },
    });
  }

  // Sắp xếp deterministic: Score cao nhất đứng đầu -> Sau đó đến title alphabet -> metadata string
  candidates.sort((a, b) => {
    if (b.score !== a.score) {
      return b.score - a.score;
    }
    return a.title.localeCompare(b.title);
  });

  return candidates.map((candidate, idx) => ({
    rank: idx + 1,
    candidate,
    llmRerankNote: null,
  }));
}
