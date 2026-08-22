import { describe, expect, it } from "vitest";
import { computeKeyResultScore, computeObjectiveScore } from "./okr-scoring";

describe("computeKeyResultScore", () => {
  it("returns 0 when target is 0 or negative", () => {
    expect(computeKeyResultScore(0, 5)).toBe(0);
    expect(computeKeyResultScore(-1, 5)).toBe(0);
  });

  it("returns the current/target ratio", () => {
    expect(computeKeyResultScore(10, 5)).toBe(0.5);
  });

  it("caps the score at 1 even when current exceeds target", () => {
    expect(computeKeyResultScore(10, 15)).toBe(1);
  });
});

describe("computeObjectiveScore", () => {
  it("returns 0 for an empty list", () => {
    expect(computeObjectiveScore([])).toBe(0);
  });

  it("averages the scores", () => {
    expect(computeObjectiveScore([0.5, 1, 0])).toBeCloseTo(0.5);
  });

  it("returns the single score for a one-element list", () => {
    expect(computeObjectiveScore([0.75])).toBe(0.75);
  });

  it("returns 1 when every key result is fully met", () => {
    expect(computeObjectiveScore([1, 1, 1])).toBe(1);
  });
});
