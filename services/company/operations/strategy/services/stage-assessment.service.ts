export interface EvidenceSummary {
  id?: number | bigint;
  sourceType: string;
  strength: number;
  confidence: number;
  supportsOrRefutes: "supports" | "refutes" | "neutral" | string;
}

export interface GateEvaluationSummary {
  stageKey: string;
  result: "passed" | "failed" | "conditional" | "pending" | string;
}

export interface StageAssessmentInput {
  currentStage?: string;
  evidenceList: EvidenceSummary[];
  passedGates?: GateEvaluationSummary[];
}

export interface StageAssessmentResult {
  recommendedStage: string;
  currentStage: string;
  rationale: string;
  supportingEvidenceCount: number;
  refutingEvidenceCount: number;
}

// M4 §3 — Project lifecycle P0..P6, ĐỘC LẬP với Workspace W0..W5.
export const PROJECT_STAGES = [
  "P0_DISCOVERY",
  "P1_PROBLEM_VALIDATION",
  "P2_SOLUTION_VALIDATION",
  "P3_BUILD_VALIDATE",
  "P4_GO_TO_MARKET",
  "P5_OPERATE_GROWTH",
  "P6_SCALE_GOVERN",
] as const;

// Alias giữ tương thích tên cũ (giá trị đã đổi sang P-set).
export const STAGES = PROJECT_STAGES;

// Map gate stageKey (có thể ghi bằng legacy S-set hoặc P-set) -> canonical P-set.
const GATE_KEY_TO_P: Record<string, string> = {
  P1_PROBLEM_VALIDATION: "P1_PROBLEM_VALIDATION",
  P2_SOLUTION_VALIDATION: "P2_SOLUTION_VALIDATION",
  P3_BUILD_VALIDATE: "P3_BUILD_VALIDATE",
  P4_GO_TO_MARKET: "P4_GO_TO_MARKET",
  P5_OPERATE_GROWTH: "P5_OPERATE_GROWTH",
  S1_PROBLEM_VALIDATION: "P1_PROBLEM_VALIDATION",
  S2_SOLUTION_VALIDATION: "P2_SOLUTION_VALIDATION",
  S3_MVP_BUILD: "P3_BUILD_VALIDATE",
  S4_PRODUCT_MARKET_FIT: "P4_GO_TO_MARKET",
  S1: "P1_PROBLEM_VALIDATION",
  S2: "P2_SOLUTION_VALIDATION",
  S3: "P3_BUILD_VALIDATE",
  S4: "P4_GO_TO_MARKET",
};

/**
 * Đánh giá Stage của Project hoàn toàn tất định (deterministic), không gọi LLM.
 * Bậc P0..P6; pass gate ở bậc N ⇒ đề xuất bậc N+1.
 */
export function assessProjectStage(input: StageAssessmentInput): StageAssessmentResult {
  const currentStage = input.currentStage || "P0_DISCOVERY";
  const passedGates = (input.passedGates || []).filter((g) => g.result === "passed");
  const passedStageKeys = new Set(
    passedGates.map((g) => GATE_KEY_TO_P[g.stageKey] ?? g.stageKey)
  );

  const supportingEvidence = input.evidenceList.filter((e) => e.supportsOrRefutes === "supports");
  const refutingEvidence = input.evidenceList.filter((e) => e.supportsOrRefutes === "refutes");

  let recommendedStage = "P0_DISCOVERY";
  let rationale = "";

  if (passedStageKeys.has("P5_OPERATE_GROWTH")) {
    recommendedStage = "P6_SCALE_GOVERN";
    rationale = "Passed P5 (Operate & Growth) gate. Recommended to advance to P6 (Scale & Govern).";
  } else if (passedStageKeys.has("P4_GO_TO_MARKET")) {
    recommendedStage = "P5_OPERATE_GROWTH";
    rationale = "Passed P4 (Go-to-Market) gate. Recommended to advance to P5 (Operate & Growth).";
  } else if (passedStageKeys.has("P3_BUILD_VALIDATE")) {
    recommendedStage = "P4_GO_TO_MARKET";
    rationale = "Passed P3 (Build & Validate) gate. Recommended to advance to P4 (Go-to-Market).";
  } else if (passedStageKeys.has("P2_SOLUTION_VALIDATION")) {
    recommendedStage = "P3_BUILD_VALIDATE";
    rationale = "Passed P2 (Solution Validation) gate. Recommended to advance to P3 (Build & Validate).";
  } else if (passedStageKeys.has("P1_PROBLEM_VALIDATION")) {
    recommendedStage = "P2_SOLUTION_VALIDATION";
    rationale = "Passed P1 (Problem Validation) gate. Recommended to advance to P2 (Solution Validation).";
  } else if (supportingEvidence.length > 0) {
    recommendedStage = "P1_PROBLEM_VALIDATION";
    rationale = `Collected ${supportingEvidence.length} supporting evidence items. P1 (Problem Validation) in progress.`;
  } else {
    recommendedStage = "P0_DISCOVERY";
    rationale = "No validated evidence or passed stage gates yet. Project is at P0 (Discovery).";
  }

  return {
    recommendedStage,
    currentStage,
    rationale,
    supportingEvidenceCount: supportingEvidence.length,
    refutingEvidenceCount: refutingEvidence.length,
  };
}
