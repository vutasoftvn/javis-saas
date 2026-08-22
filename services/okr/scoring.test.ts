import { describe, expect, it } from "vitest";
import { computeKeyResultScore, computeObjectiveScore } from "./scoring";

describe("computeKeyResultScore", () => {
  it("returns 0 when current value is 0", () => {
    expect(computeKeyResultScore(100, 0)).toBe(0);
  });

  it("returns 1 when current value meets target", () => {
    expect(computeKeyResultScore(100, 100)).toBe(1);
  });

  it("returns a fraction for partial progress", () => {
    expect(computeKeyResultScore(100, 25)).toBe(0.25);
  });

  it("clamps at 1 when current value exceeds target", () => {
    expect(computeKeyResultScore(100, 150)).toBe(1);
  });

  it("returns 0 when target is 0 (avoids division by zero)", () => {
    expect(computeKeyResultScore(0, 0)).toBe(0);
  });
});

describe("computeObjectiveScore", () => {
  it("averages key result scores", () => {
    expect(computeObjectiveScore([1, 0.5, 0])).toBeCloseTo(0.5);
  });

  it("returns 0 for an objective with no key results", () => {
    expect(computeObjectiveScore([])).toBe(0);
  });
});
