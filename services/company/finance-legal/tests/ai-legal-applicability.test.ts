import { describe, expect, it } from "vitest";
import {
  assessAiApplicability,
  assessWorkspaceAiApplicability,
  evaluateAiRule,
  type AiApplicabilityInput,
  type AiApplicabilityRule,
} from "../services/ai-legal-applicability.service";

describe("AI legal applicability service", () => {
  const workspaceId = "704434052995743744";

  const privateBusinessAdvisoryInput: AiApplicabilityInput = {
    workspaceId,
    deploymentMode: "ADVISORY_ONLY",
    intendedPurpose: "private-business financial advisory and drafting",
    decisionDomain: "FINANCE",
    capabilityEffectClass: "DRAFT",
    dataCategories: ["BUSINESS_CONFIDENTIAL"],
    providerProfileStatus: "APPROVED",
    lastAssessmentAt: new Date().toISOString(),
  };

  it("blocks a prohibited automated hiring purpose even when a tenant wants ALLOW", async () => {
    const result = await assessAiApplicability({
      workspaceId,
      deploymentMode: "ADVISORY_ONLY",
      intendedPurpose: "candidate ranking",
      decisionDomain: "HR",
      capabilityEffectClass: "EXTERNAL",
      dataCategories: ["PERSONAL"],
      providerProfileStatus: "APPROVED",
      lastAssessmentAt: "2026-08-29T00:00:00Z",
    });
    expect(result.currentLawBlocks).toContain("PROHIBITED_DECISION_DOMAIN");
  });

  it("returns policy-watch information without a blocking result", async () => {
    const result = await assessAiApplicability(privateBusinessAdvisoryInput);
    expect(result.currentLawBlocks).toEqual([]);
    expect(result.policyWatchItems.length).toBeGreaterThan(0);
  });

  it("blocks non-advisory deployment mode", async () => {
    const result = await assessAiApplicability({
      ...privateBusinessAdvisoryInput,
      deploymentMode: "AUTONOMOUS",
    });
    expect(result.currentLawBlocks).toContain("NON_ADVISORY_MODE");
  });

  it("blocks unapproved provider profile", async () => {
    const result = await assessAiApplicability({
      ...privateBusinessAdvisoryInput,
      providerProfileStatus: "DRAFT",
    });
    expect(result.currentLawBlocks).toContain("PROVIDER_NOT_APPROVED");
  });

  it("requires professional review for complex legal analysis", async () => {
    const result = await assessAiApplicability({
      ...privateBusinessAdvisoryInput,
      decisionDomain: "LEGAL",
      intendedPurpose: "complex litigation dispute strategy",
      capabilityEffectClass: "EXTERNAL",
    });
    expect(result.professionalReviewRequired.length).toBeGreaterThan(0);
  });

  it("pure predicate evaluator evaluates rule layers correctly", () => {
    const rule: AiApplicabilityRule = {
      id: "rule_1",
      layer: "CURRENT_LAW",
      effect: "BLOCK",
      reasonCode: "PROHIBITED_DECISION_DOMAIN",
      predicate: { decisionDomain: "HR" },
    };

    expect(evaluateAiRule(rule, { ...privateBusinessAdvisoryInput, decisionDomain: "HR" })).toBe("BLOCK");
    expect(evaluateAiRule(rule, privateBusinessAdvisoryInput)).toBe("NO_MATCH");
  });
});
