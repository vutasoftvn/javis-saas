export interface StagePolicyRule {
  key: string;
  description: string;
  minCount?: number;
  minStrength?: number;
  sourceType?: string;
}

export interface StagePolicyData {
  id?: number | bigint | string;
  stageKey: string;
  minimumEvidenceScore: number;
  requirements: StagePolicyRule[] | any;
  blockingRiskRules?: string[] | any;
}

export interface EvidenceItem {
  id?: number | bigint | string;
  sourceType: string;
  strength: number;
  confidence: number;
  supportsOrRefutes: "supports" | "refutes" | "neutral" | string;
}

export interface BlockingRiskItem {
  riskKey: string;
  severity: "high" | "critical" | "medium" | "low" | string;
  resolved: boolean;
  notes?: string;
}

export interface GateEvaluationInput {
  policy: StagePolicyData;
  evidenceList: EvidenceItem[];
  blockingRisks?: BlockingRiskItem[];
  humanOverride?: boolean;
}

export interface GateEvaluationOutput {
  requirementsMet: boolean;
  evidenceScore: number;
  blockingRisks: BlockingRiskItem[];
  result: "passed" | "failed" | "conditional";
  rationale: string;
  humanOverride: boolean;
}

/**
 * Đánh giá Stage Gate hoàn toàn tất định (100% deterministic), KHÔNG gọi LLM.
 * Các tiêu chí:
 * 1. Average evidence strength của các supporting evidence >= policy.minimumEvidenceScore
 * 2. Từng requirement trong policy.requirements được kiểm tra
 * 3. Không có rủi ro cản trở (blocking risks) chưa được giải quyết ở mức high/critical
 */
export function evaluateGate(input: GateEvaluationInput): GateEvaluationOutput {
  const { policy, evidenceList, blockingRisks = [], humanOverride = false } = input;

  const supporting = evidenceList.filter((e) => e.supportsOrRefutes === "supports");
  const refuting = evidenceList.filter((e) => e.supportsOrRefutes === "refutes");

  // 1. Calculate average evidence score
  let evidenceScore = 0;
  if (supporting.length > 0) {
    const totalScore = supporting.reduce((acc, curr) => acc + (curr.strength * curr.confidence), 0);
    evidenceScore = Math.round((totalScore / supporting.length) * 10000) / 10000;
  }

  // 2. Check blocking risks
  const unresolvedBlockingRisks = blockingRisks.filter(
    (r) => !r.resolved && (r.severity === "high" || r.severity === "critical")
  );

  // 3. Check requirements
  const rawRequirements: StagePolicyRule[] = Array.isArray(policy.requirements) ? policy.requirements : [];
  const failedRequirements: string[] = [];

  for (const req of rawRequirements) {
    if (req.minCount) {
      let count = supporting.length;
      if (req.sourceType) {
        count = supporting.filter((e) => e.sourceType.toLowerCase() === req.sourceType?.toLowerCase()).length;
      }
      if (count < req.minCount) {
        failedRequirements.push(`Requirement '${req.description || req.key}': requires at least ${req.minCount} items, found ${count}.`);
      }
    }
    if (req.minStrength && evidenceScore < req.minStrength) {
      failedRequirements.push(`Requirement '${req.description || req.key}': requires average strength >= ${req.minStrength}, got ${evidenceScore}.`);
    }
  }

  const scoreMet = evidenceScore >= (policy.minimumEvidenceScore || 0);
  if (!scoreMet && (policy.minimumEvidenceScore || 0) > 0) {
    failedRequirements.push(`Overall evidence score ${evidenceScore} is below minimum requirement ${policy.minimumEvidenceScore}.`);
  }

  const hasExcessiveRefutation = refuting.length > supporting.length && refuting.length > 0;
  if (hasExcessiveRefutation) {
    failedRequirements.push(`Refuting evidence (${refuting.length}) exceeds supporting evidence (${supporting.length}).`);
  }

  const requirementsMet = failedRequirements.length === 0 && unresolvedBlockingRisks.length === 0;

  let result: "passed" | "failed" | "conditional" = "failed";
  let rationale = "";

  if (humanOverride) {
    result = "passed";
    rationale = `Gate passed via human override. (Auto-evaluation notes: requirementsMet=${requirementsMet}, evidenceScore=${evidenceScore}).`;
  } else if (requirementsMet) {
    result = "passed";
    rationale = `All gate requirements met for stage ${policy.stageKey}. Evidence score: ${evidenceScore} (min: ${policy.minimumEvidenceScore}). Supporting evidence items: ${supporting.length}.`;
  } else if (unresolvedBlockingRisks.length > 0) {
    result = "failed";
    rationale = `Gate failed due to ${unresolvedBlockingRisks.length} unresolved critical/high blocking risk(s). ${failedRequirements.join(" ")}`.trim();
  } else if (!scoreMet || failedRequirements.length > 0) {
    result = "failed";
    rationale = `Gate failed: ${failedRequirements.join(" ")}`;
  }

  return {
    requirementsMet,
    evidenceScore,
    blockingRisks: unresolvedBlockingRisks,
    result,
    rationale,
    humanOverride,
  };
}
