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

  // Migration 31 — rule DB thật STATUTORY_PROHIBITED_DOMAINS đang ở
  // review_status='PENDING_REVIEW' (chưa có luật sư/chuyên gia pháp lý xác
  // nhận review thật — xem docs/legal/ai-regulatory-source-register.md).
  // Engine KHÔNG được tự động BLOCK theo luật chưa qua thẩm định con người,
  // nhưng cũng không được lờ đi: phải bắt buộc PROFESSIONAL_REVIEW_REQUIRED.
  it("requires professional review (not an automatic BLOCK) for a prohibited automated hiring purpose while the rule is pending legal review", async () => {
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
    expect(result.currentLawBlocks).not.toContain("PROHIBITED_DECISION_DOMAIN");
    expect(result.blockingRule).toBeUndefined();
    expect(result.professionalReviewRequired).toContain("PROHIBITED_DECISION_DOMAIN");
  });

  it("returns policy-watch information without a blocking result", async () => {
    const result = await assessAiApplicability(privateBusinessAdvisoryInput);
    expect(result.currentLawBlocks).toEqual([]);
    expect(result.policyWatchItems.length).toBeGreaterThan(0);
  });

  // Migration 31 — rule DB thật STATUTORY_MODE_ADVISORY cũng đang
  // PENDING_REVIEW, cùng lý do trên.
  it("requires professional review (not an automatic BLOCK) for non-advisory deployment mode while the rule is pending legal review", async () => {
    const result = await assessAiApplicability({
      ...privateBusinessAdvisoryInput,
      deploymentMode: "AUTONOMOUS",
    });
    expect(result.currentLawBlocks).not.toContain("NON_ADVISORY_MODE");
    expect(result.blockingRule).toBeUndefined();
    expect(result.professionalReviewRequired).toContain("NON_ADVISORY_MODE");
  });

  // Migration 31 — rule DB thật STATUTORY_PROVIDER_APPROVED cũng đang
  // PENDING_REVIEW, cùng lý do trên.
  it("requires professional review (not an automatic BLOCK) for an unapproved provider profile while the rule is pending legal review", async () => {
    const result = await assessAiApplicability({
      ...privateBusinessAdvisoryInput,
      providerProfileStatus: "DRAFT",
    });
    expect(result.currentLawBlocks).not.toContain("PROVIDER_NOT_APPROVED");
    expect(result.blockingRule).toBeUndefined();
    expect(result.professionalReviewRequired).toContain("PROVIDER_NOT_APPROVED");
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
