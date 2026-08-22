import { EvidenceItem, GateEvaluationOutput } from "./gate-evaluation.service";

export type StrategyDecision = "proceed" | "pivot" | "kill" | "hold";

export interface RecordDecisionInput {
  projectId: number | bigint | string;
  gateEvaluationId?: number | bigint | string | null;
  gateEvaluation?: GateEvaluationOutput;
  decision: StrategyDecision;
  actorWorkforceMemberId?: number | bigint | string | null;
  evidenceList: EvidenceItem[];
  notes?: string;
}

export interface EvidenceSnapshot {
  evaluatedAt: string;
  totalEvidenceCount: number;
  supportingCount: number;
  refutingCount: number;
  averageStrength: number;
  items: Array<{
    id?: number | bigint | string;
    sourceType: string;
    strength: number;
    confidence: number;
    supportsOrRefutes: string;
  }>;
  gateEvaluationSummary?: {
    requirementsMet: boolean;
    evidenceScore: number;
    result: string;
    rationale: string;
  };
  decisionNotes?: string;
}

export interface DecisionRecordPayload {
  projectId: number | bigint | string;
  gateEvaluationId?: number | bigint | string | null;
  decision: StrategyDecision;
  actorWorkforceMemberId?: number | bigint | string | null;
  evidenceSnapshot: EvidenceSnapshot;
  createdAt: string;
}

/**
 * Đóng gói bản ghi quyết định chiến lược và snapshot evidence tại thời điểm quyết định.
 * Hàm thuần tất định, không gọi LLM.
 */
export function buildDecisionRecord(input: RecordDecisionInput): DecisionRecordPayload {
  const {
    projectId,
    gateEvaluationId,
    gateEvaluation,
    decision,
    actorWorkforceMemberId,
    evidenceList,
    notes,
  } = input;

  const supporting = evidenceList.filter((e) => e.supportsOrRefutes === "supports");
  const refuting = evidenceList.filter((e) => e.supportsOrRefutes === "refutes");

  const avgStrength = evidenceList.length > 0
    ? Math.round((evidenceList.reduce((acc, curr) => acc + curr.strength, 0) / evidenceList.length) * 10000) / 10000
    : 0;

  const evidenceSnapshot: EvidenceSnapshot = {
    evaluatedAt: new Date().toISOString(),
    totalEvidenceCount: evidenceList.length,
    supportingCount: supporting.length,
    refutingCount: refuting.length,
    averageStrength: avgStrength,
    items: evidenceList.map((e) => ({
      id: e.id,
      sourceType: e.sourceType,
      strength: e.strength,
      confidence: e.confidence,
      supportsOrRefutes: e.supportsOrRefutes,
    })),
    gateEvaluationSummary: gateEvaluation ? {
      requirementsMet: gateEvaluation.requirementsMet,
      evidenceScore: gateEvaluation.evidenceScore,
      result: gateEvaluation.result,
      rationale: gateEvaluation.rationale,
    } : undefined,
    decisionNotes: notes,
  };

  return {
    projectId,
    gateEvaluationId: gateEvaluationId ?? null,
    decision,
    actorWorkforceMemberId: actorWorkforceMemberId ?? null,
    evidenceSnapshot,
    createdAt: new Date().toISOString(),
  };
}
