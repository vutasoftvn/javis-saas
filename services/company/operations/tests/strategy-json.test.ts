import { describe, expect, it } from "vitest";
import {
  evaluateGate,
  parseStagePolicyRules,
  toStagePolicyRules,
} from "../strategy/services/gate-evaluation.service";
import { toJsonArray, toJsonObject } from "../strategy/services/strategy-json";

describe("Strategy persisted JSON decoding", () => {
  it("fails closed for malformed JSON objects and arrays", () => {
    expect(toJsonObject(["not", "an", "object"])).toEqual({});
    expect(toJsonObject(new Date())).toEqual({});
    expect(toJsonArray({ not: "an array" })).toEqual([]);
    expect(toJsonArray(["valid", () => "not JSON"])).toEqual([]);
    expect(toJsonArray([Number.NaN])).toEqual([]);
  });

  it("keeps only complete stage policy rules from persisted JSON", () => {
    const rules = toStagePolicyRules([
      { key: "evidence", description: "At least one evidence item", minCount: 1 },
      { key: "count-only", minCount: 2 },
      { description: "missing key" },
      { key: "bad-minimum", description: "Bad minimum", minStrength: "high" },
    ]);

    expect(rules).toEqual([
      { key: "evidence", description: "At least one evidence item", minCount: 1 },
      { key: "count-only", minCount: 2 },
    ]);
  });

  it("fails a gate when persisted stage policy requirements are malformed", () => {
    const parsed = parseStagePolicyRules([
      { key: "evidence", minCount: 1 },
      { key: "bad-minimum", description: "Bad minimum", minStrength: "high" },
    ]);

    expect(parsed.rules).toEqual([{ key: "evidence", minCount: 1 }]);
    expect(parsed.invalidCount).toBe(1);

    const evaluation = evaluateGate({
      policy: {
        stageKey: "P1",
        minimumEvidenceScore: 0,
        requirements: parsed.rules,
        invalidRequirementCount: parsed.invalidCount,
      },
      evidenceList: [],
    });

    expect(evaluation.result).toBe("failed");
    expect(evaluation.rationale).toContain("invalid requirement");
  });

  it("fails a gate when persisted stage policy requirements are not an array", () => {
    const parsed = parseStagePolicyRules({ key: "not-an-array" });

    expect(parsed.rules).toEqual([]);
    expect(parsed.invalidCount).toBe(1);

    const evaluation = evaluateGate({
      policy: {
        stageKey: "P1",
        minimumEvidenceScore: 0,
        requirements: parsed.rules,
        invalidRequirementCount: parsed.invalidCount,
      },
      evidenceList: [],
    });

    expect(evaluation.result).toBe("failed");
  });
});
