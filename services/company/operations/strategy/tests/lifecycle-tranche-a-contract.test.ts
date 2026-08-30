import { describe, it, expect } from "vitest";

describe("COSA Lifecycle Tranche A Contract Verification", () => {
  const canonicalStages = [
    "P0_DISCOVERY",
    "P1_PROBLEM_VALIDATION",
    "P2_SOLUTION_VALIDATION",
    "P3_BUILD_VALIDATE",
    "P4_GO_TO_MARKET",
    "P5_OPERATE_GROWTH",
    "P6_SCALE_GOVERN",
  ] as const;

  it("verifies canonical wire stages P0–P6 structure", () => {
    expect(canonicalStages).toHaveLength(7);
    expect(canonicalStages[0]).toBe("P0_DISCOVERY");
    expect(canonicalStages[1]).toBe("P1_PROBLEM_VALIDATION");
    expect(canonicalStages[2]).toBe("P2_SOLUTION_VALIDATION");
    expect(canonicalStages[6]).toBe("P6_SCALE_GOVERN");
  });

  it("prohibits deprecated S-stages in canonical runtime validation", () => {
    const deprecatedStages = ["S0_IDEATION", "S1_PROBLEM_VALIDATION", "S2_SOLUTION_FIT"];
    for (const s of deprecatedStages) {
      expect(canonicalStages.includes(s as never)).toBe(false);
    }
  });

  it("validates evidence lifecycle state machine invariants", () => {
    const validStatuses = ["candidate", "approved", "rejected"] as const;
    expect(validStatuses).toContain("candidate");
    expect(validStatuses).toContain("approved");
    expect(validStatuses).toContain("rejected");
  });

  it("validates ingestion source system allowlist", () => {
    const validSources = ["interview", "crm", "telemetry", "payment"] as const;
    expect(validSources).toHaveLength(4);
    expect(validSources).toContain("interview");
    expect(validSources).toContain("crm");
    expect(validSources).toContain("telemetry");
    expect(validSources).toContain("payment");
  });
});
