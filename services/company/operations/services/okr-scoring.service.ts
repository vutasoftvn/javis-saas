import { computeLinearProgress } from "./execution-outcome.service";

export { computeLinearProgress };

export type KrScoringType = "LINEAR_INCREASE" | "LINEAR_DECREASE" | "MILESTONE" | "RANGE";

export interface ComputeProgressInput {
  baseline?: number | null;
  target?: number | null;
  current?: number | null;
  scoringType?: KrScoringType | string | null;
}

/**
 * Computes progress toward Key Result goal considering scoring type and baseline.
 * Target attainment and baseline progress are clearly distinct.
 */
export function computeKeyResultProgress(input: ComputeProgressInput): number | null {
  const { baseline, target, current, scoringType = "LINEAR_INCREASE" } = input;

  if (target === null || target === undefined || current === null || current === undefined) {
    return null;
  }
  if (!Number.isFinite(target) || !Number.isFinite(current)) {
    return null;
  }

  if (scoringType === "MILESTONE") {
    return current >= target ? 1.0 : 0.0;
  }

  if (scoringType === "RANGE") {
    if (baseline === null || baseline === undefined || !Number.isFinite(baseline)) {
      return null;
    }
    const [minVal, maxVal] = baseline <= target ? [baseline, target] : [target, baseline];
    return current >= minVal && current <= maxVal ? 1.0 : 0.0;
  }

  // LINEAR_INCREASE or LINEAR_DECREASE
  return computeLinearProgress({ baseline: baseline ?? 0, target, current });
}

/**
 * Legacy target attainment ratio (current / target).
 */
export function computeKeyResultScore(targetValue: number, currentValue: number): number {
  if (targetValue <= 0) return 0;
  return Math.min(Math.max(0, currentValue / targetValue), 1);
}

export function computeObjectiveScore(scores: number[]): number {
  if (scores.length === 0) return 0;
  return scores.reduce((sum, score) => sum + score, 0) / scores.length;
}
