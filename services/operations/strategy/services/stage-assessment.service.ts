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

export const STAGES = [
  "S0_GENESIS",
  "S1_PROBLEM_VALIDATION",
  "S2_SOLUTION_VALIDATION",
  "S3_MVP_BUILD",
  "S4_PRODUCT_MARKET_FIT",
  "S5_SCALE",
] as const;

/**
 * Đánh giá Stage của Project hoàn toàn tất định (deterministic), không gọi LLM.
 * Quy tắc:
 * 1. Không có bằng chứng / không có gate passed -> S0_GENESIS hoặc S1_PROBLEM_VALIDATION
 * 2. Đã pass gate S1 -> Đề xuất S2_SOLUTION_VALIDATION
 * 3. Đã pass gate S2 -> Đề xuất S3_MVP_BUILD
 * 4. Đã pass gate S3 -> Đề xuất S4_PRODUCT_MARKET_FIT
 * 5. Đã pass gate S4 -> Đề xuất S5_SCALE
 */
export function assessProjectStage(input: StageAssessmentInput): StageAssessmentResult {
  const currentStage = input.currentStage || "S0_GENESIS";
  const passedGates = (input.passedGates || []).filter((g) => g.result === "passed");
  const passedStageKeys = new Set(passedGates.map((g) => g.stageKey));

  const supportingEvidence = input.evidenceList.filter((e) => e.supportsOrRefutes === "supports");
  const refutingEvidence = input.evidenceList.filter((e) => e.supportsOrRefutes === "refutes");

  let recommendedStage = "S0_GENESIS";
  let rationale = "";

  if (passedStageKeys.has("S4_PRODUCT_MARKET_FIT") || passedStageKeys.has("S4")) {
    recommendedStage = "S5_SCALE";
    rationale = "Passed Stage 4 (Product-Market Fit) gate evaluation. Recommended to advance to Stage 5 (Scale).";
  } else if (passedStageKeys.has("S3_MVP_BUILD") || passedStageKeys.has("S3")) {
    recommendedStage = "S4_PRODUCT_MARKET_FIT";
    rationale = "Passed Stage 3 (MVP Build) gate evaluation. Recommended to advance to Stage 4 (Product-Market Fit).";
  } else if (passedStageKeys.has("S2_SOLUTION_VALIDATION") || passedStageKeys.has("S2")) {
    recommendedStage = "S3_MVP_BUILD";
    rationale = "Passed Stage 2 (Solution Validation) gate evaluation. Recommended to advance to Stage 3 (MVP Build).";
  } else if (passedStageKeys.has("S1_PROBLEM_VALIDATION") || passedStageKeys.has("S1")) {
    recommendedStage = "S2_SOLUTION_VALIDATION";
    rationale = "Passed Stage 1 (Problem Validation) gate evaluation. Recommended to advance to Stage 2 (Solution Validation).";
  } else if (supportingEvidence.length > 0) {
    recommendedStage = "S1_PROBLEM_VALIDATION";
    rationale = `Collected ${supportingEvidence.length} supporting evidence items. Recommended Stage 1 (Problem Validation) in progress.`;
  } else {
    recommendedStage = "S0_GENESIS";
    rationale = "No validated evidence or passed stage gates yet. Project is at Genesis stage.";
  }

  return {
    recommendedStage,
    currentStage,
    rationale,
    supportingEvidenceCount: supportingEvidence.length,
    refutingEvidenceCount: refutingEvidence.length,
  };
}
