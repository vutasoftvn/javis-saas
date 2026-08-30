import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import {
  assessAiApplicability,
  fetchActiveExecutableRules,
  type AiApplicabilityInput,
  type ExecutableRule,
} from "../services/ai-legal-applicability.service";
import {
  resolveApprovedComplianceSnapshot,
  computeCanonicalSha256,
} from "../services/ai-compliance-snapshot.service";

const {
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceEvidence,
  aiProviderProfiles,
  aiDataProcessingProfiles,
  aiSystemCatalog,
  aiSystemVersions,
  aiSystemCapabilityBindings,
  regulationVersions,
  aiApplicabilityRules,
} = schema;

describe("AI Legal Provenance & Tamper-Detection (Task 6)", () => {
  const workspaceId = generateSnowflake();

  it("does not emit a CURRENT_LAW control from an unverified source version", async () => {
    const unverifiedRule: ExecutableRule = {
      ruleId: "UNVERIFIED_TEST_RULE",
      ruleVersion: "1.0.0",
      sourceVersionId: "9999",
      sourceContentHash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", // placeholder empty hash
      effectiveFrom: "2026-01-01",
      effectiveTo: null,
      reviewStatus: "UNVERIFIED",
      layer: "CURRENT_LAW",
      effect: "BLOCK",
      reasonCode: "UNVERIFIED_SOURCE_HIT",
      predicate: { deploymentModeNotEquals: "ADVISORY_ONLY" },
    };

    const unverifiedDeployment: AiApplicabilityInput = {
      workspaceId: String(workspaceId),
      deploymentMode: "AUTONOMOUS",
      intendedPurpose: "general autonomous operations",
      decisionDomain: "OPERATIONS",
      providerProfileStatus: "APPROVED",
    };

    // Khi chạy với unverified rule, assessAiApplicability không phát ra blockingRule hay CURRENT_LAW block
    const result = await assessAiApplicability(unverifiedDeployment, { rules: [unverifiedRule] });
    expect(result).toEqual(
      expect.not.objectContaining({ blockingRule: expect.anything() })
    );
    expect(result.currentLawBlocks).toEqual([]);
  });

  it("evaluates date boundaries: inactive before effective date, inactive after expiry", async () => {
    const dateBoundedRule: ExecutableRule = {
      ruleId: "DATE_BOUNDED_RULE",
      ruleVersion: "1.0.0",
      sourceVersionId: "212",
      sourceContentHash: "f51e30980912a04ac347e34577779b42545285ad2df3c9f0cec5929b69a0e99b",
      effectiveFrom: "2026-08-15",
      effectiveTo: "2026-12-31",
      reviewStatus: "REVIEWED",
      layer: "CURRENT_LAW",
      effect: "BLOCK",
      reasonCode: "PROHIBITED_DECISION_DOMAIN",
      predicate: { isProhibitedDomain: true },
    };

    const hrDeployment: AiApplicabilityInput = {
      workspaceId: String(workspaceId),
      deploymentMode: "ADVISORY_ONLY",
      intendedPurpose: "automated candidate screening",
      decisionDomain: "HR",
      providerProfileStatus: "APPROVED",
    };

    // 1. Trước ngày hiệu lực (2026-08-01): rule không kích hoạt
    const beforeResult = await assessAiApplicability(
      { ...hrDeployment, asOfDate: "2026-08-01T00:00:00Z" },
      { rules: [dateBoundedRule] }
    );
    expect(beforeResult.currentLawBlocks).not.toContain("PROHIBITED_DECISION_DOMAIN");
    expect(beforeResult.blockingRule).toBeUndefined();

    // 2. Trong thời gian hiệu lực (2026-08-20): rule kích hoạt BLOCK
    const activeResult = await assessAiApplicability(
      { ...hrDeployment, asOfDate: "2026-08-20T00:00:00Z" },
      { rules: [dateBoundedRule] }
    );
    expect(activeResult.currentLawBlocks).toContain("PROHIBITED_DECISION_DOMAIN");
    expect(activeResult.blockingRule?.ruleId).toBe("DATE_BOUNDED_RULE");

    // 3. Sau ngày hết hiệu lực (2027-01-05): rule không còn hiệu lực
    const expiredResult = await assessAiApplicability(
      { ...hrDeployment, asOfDate: "2027-01-05T00:00:00Z" },
      { rules: [dateBoundedRule] }
    );
    expect(expiredResult.currentLawBlocks).not.toContain("PROHIBITED_DECISION_DOMAIN");
  });

  it("filters out inactive or superseded regulation versions from database fetch", async () => {
    const rules = await fetchActiveExecutableRules(new Date("2026-08-30"));
    expect(rules.length).toBeGreaterThan(0);

    // Không có rule nào gắn với version seed 28 cũ (110-117) đã bị đánh dấu INACTIVE_CORRECTION
    const oldVersionIds = new Set(["110", "111", "112", "113", "114", "115", "116", "117"]);
    for (const r of rules) {
      expect(oldVersionIds.has(r.sourceVersionId)).toBe(false);
      expect(r.sourceContentHash).not.toBe("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    }
  });

  it("tamper detection: changing an evidence hash or source version hash produces a different snapshot hash", async () => {
    const basePayload = {
      workspaceId: "704434052995743744",
      deploymentId: "704434052995743745",
      assessmentId: "704434052995743746",
      assessmentExpiresAt: "2027-01-01T00:00:00.000Z",
      capabilityBindingIds: ["704434052995743750"],
      evidence: [
        { id: "1", contentHash: "sha256:original-evidence-hash" },
      ],
      legalVersions: [
        { id: "210", contentHash: "53be2f9993e5060cc0ce723fc506d6535c9358978dbbeff11324c8d6236cae69" },
      ],
      providerProfileId: "704434052995743751",
      providerProfileVersion: "v1",
      modelKey: "deepseek-chat",
      dataProfileId: "704434052995743752",
      dataProfileVersion: "v1",
      policySnapshotHash: "sha256:policy-hash-1",
      issuedAt: "2026-08-30T10:00:00.000Z",
      expiresAt: "2027-01-01T00:00:00.000Z",
    };

    const originalHash = computeCanonicalSha256(basePayload);

    // 1. Thay đổi hash của evidence -> snapshotHash phải đổi
    const tamperedEvidencePayload = {
      ...basePayload,
      evidence: [
        { id: "1", contentHash: "sha256:tampered-evidence-hash" },
      ],
    };
    const tamperedEvidenceHash = computeCanonicalSha256(tamperedEvidencePayload);
    expect(tamperedEvidenceHash).not.toBe(originalHash);

    // 2. Thay đổi hash của quy phạm pháp luật -> snapshotHash phải đổi
    const tamperedLegalPayload = {
      ...basePayload,
      legalVersions: [
        { id: "210", contentHash: "sha256:tampered-law-content-hash" },
      ],
    };
    const tamperedLegalHash = computeCanonicalSha256(tamperedLegalPayload);
    expect(tamperedLegalHash).not.toBe(originalHash);
  });
});
