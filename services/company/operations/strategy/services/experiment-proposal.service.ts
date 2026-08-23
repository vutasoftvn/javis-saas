import { RankedAssumption } from "./assumption-ranking.service";

export interface ExperimentProposal {
  assumptionId: number | bigint | string;
  projectId: number | bigint | string;
  hypothesis: string;
  method: string;
  successCriteria: string;
  budget: number;
  status: "draft";
  rationale: string;
}

export interface ExistingExperimentSummary {
  assumptionId?: number | bigint | string | null;
}

/**
 * Đề xuất khung experiment mẫu từ top assumption chưa có experiment liên kết.
 * Service thuần tạo template tất định, không gọi LLM. Các chi tiết cụ thể
 * sẽ được tinh chỉnh bởi agent/skill ở tầng trên nếu cần.
 */
export function proposeExperimentsForAssumptions(
  assumptions: RankedAssumption[],
  existingExperiments: ExistingExperimentSummary[] = [],
  maxProposals: number = 3
): ExperimentProposal[] {
  const coveredAssumptionIds = new Set(
    existingExperiments
      .map((e) => e.assumptionId)
      .filter((id): id is number | bigint | string => id !== null && id !== undefined)
      .map((id) => String(id))
  );

  const untestedAssumptions = assumptions.filter(
    (a) => !coveredAssumptionIds.has(String(a.id)) && a.status !== "validated" && a.status !== "invalidated"
  );

  const proposals: ExperimentProposal[] = [];

  for (const assumption of untestedAssumptions.slice(0, maxProposals)) {
    // Determine method template based on uncertainty and importance
    let method = "customer_interview";
    let successCriteria = "At least 5 out of 10 targeted customer interviews confirm the problem exists with high severity.";

    if (assumption.importance >= 8 && assumption.uncertainty >= 7) {
      method = "concierge_or_smoke_test";
      successCriteria = "Conversion rate >= 5% on landing page signups or pre-orders.";
    } else if (assumption.importance >= 6) {
      method = "customer_discovery_interviews";
      successCriteria = ">= 70% positive intent across 10 structured stakeholder interviews.";
    }

    proposals.push({
      assumptionId: assumption.id,
      projectId: assumption.projectId,
      hypothesis: `We believe that: "${assumption.statement}". We will know we are right when: ${successCriteria}`,
      method,
      successCriteria,
      budget: 0,
      status: "draft",
      rationale: `Derived deterministically from high-risk assumption (rank #${assumption.rank}, risk score: ${assumption.computedRiskScore}).`,
    });
  }

  return proposals;
}
