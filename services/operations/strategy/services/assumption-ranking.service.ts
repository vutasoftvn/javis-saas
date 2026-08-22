export interface AssumptionInput {
  id: number | bigint | string;
  projectId: number | bigint | string;
  statement: string;
  importance: number;
  uncertainty: number;
  status?: string;
  riskScore?: number;
}

export interface RankedAssumption extends AssumptionInput {
  computedRiskScore: number;
  rank: number;
}

/**
 * Xếp hạng các assumption hoàn toàn tất định theo: riskScore = importance * uncertainty (giảm dần).
 * Trường hợp bằng điểm (tie-break): ưu tiên theo statement alphabet rồi đến id.
 */
export function rankAssumptions(assumptions: AssumptionInput[]): RankedAssumption[] {
  const scored = assumptions.map((a) => {
    const importance = Math.max(1, Math.min(10, a.importance || 1));
    const uncertainty = Math.max(1, Math.min(10, a.uncertainty || 1));
    const computedRiskScore = importance * uncertainty;
    return {
      ...a,
      importance,
      uncertainty,
      computedRiskScore,
    };
  });

  scored.sort((a, b) => {
    // 1. Higher risk score first
    if (b.computedRiskScore !== a.computedRiskScore) {
      return b.computedRiskScore - a.computedRiskScore;
    }
    // 2. Higher uncertainty first
    if (b.uncertainty !== a.uncertainty) {
      return b.uncertainty - a.uncertainty;
    }
    // 3. Higher importance first
    if (b.importance !== a.importance) {
      return b.importance - a.importance;
    }
    // 4. Deterministic string tie-break
    if (a.statement !== b.statement) {
      return a.statement.localeCompare(b.statement);
    }
    // 5. ID tie-break
    return String(a.id).localeCompare(String(b.id));
  });

  return scored.map((item, index) => ({
    ...item,
    rank: index + 1,
  }));
}
