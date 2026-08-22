export function computeKeyResultScore(targetValue: number, currentValue: number): number {
  if (targetValue <= 0) return 0;
  return Math.min(currentValue / targetValue, 1);
}

export function computeObjectiveScore(scores: number[]): number {
  if (scores.length === 0) return 0;
  return scores.reduce((sum, score) => sum + score, 0) / scores.length;
}
