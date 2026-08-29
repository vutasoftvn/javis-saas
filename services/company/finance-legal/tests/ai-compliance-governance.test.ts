import { describe, expect, it } from "vitest";
import {
  createAiDeployment,
  submitAiAssessment,
  approveAiAssessment,
  suspendAiDeployment,
  resumeAiDeployment,
  getComplianceCenterView,
  getDeployment,
  type CreateAiDeploymentInput,
} from "../services/ai-compliance-governance.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { aiSystemCatalog, aiSystemVersions, aiProviderProfiles, aiDataProcessingProfiles, aiComplianceEvidence } = schema;

describe("AI compliance governance service", () => {
  const workspaceId = String(generateSnowflake());
  const otherWorkspaceId = String(generateSnowflake());
  const founderId = String(generateSnowflake());
  const technicalOwnerId = String(generateSnowflake());

  async function seedCatalogAndVersion() {
    const catalogId = generateSnowflake();
    const versionId = generateSnowflake();

    await db.insert(aiSystemCatalog).values({
      id: catalogId,
      systemKey: `cosa-advisory-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: "COSA Advisory Agent",
      allowedPurposes: ["private-business advisory"],
      prohibitedPurposes: ["automated hiring", "credit scoring"],
      lifecycleStatus: "ACTIVE",
    });

    await db.insert(aiSystemVersions).values({
      id: versionId,
      systemCatalogId: catalogId,
      version: "1.0.0",
      configHash: "sha256:abc123config",
      status: "ACTIVE",
    });

    return { catalogId: String(catalogId), versionId: String(versionId) };
  }

  async function seedApprovedProviderAndDataProfile(wsId: string, deploymentId: string | bigint) {
    const providerProfileId = generateSnowflake();

    const dataProfileId = generateSnowflake();

    await db.insert(aiProviderProfiles).values({
      id: providerProfileId,
      workspaceId: BigInt(wsId),
      providerKey: "deepseek",
      modelKey: "deepseek-chat",
      version: "v3",
      status: "APPROVED",
      declaredProcessingRegion: "SG",
      dpaReference: "dpa://legal/deepseek-2026",
      allowedDataCategories: ["BUSINESS_CONFIDENTIAL"],
    });

    await db.insert(aiDataProcessingProfiles).values({
      id: dataProfileId,
      workspaceId: BigInt(wsId),
      deploymentId: BigInt(deploymentId),
      purposeId: "private-business-advisory",
      dataCategories: ["BUSINESS_CONFIDENTIAL"],
      recipientProviderProfileId: providerProfileId,
      retentionPolicyId: "retention-30d",
      version: "v1",
      status: "ACTIVE",
    });

    return { providerProfileId: String(providerProfileId), dataProfileId: String(dataProfileId) };
  }

  it("requires Founder approval of the exact assessment before activation", async () => {
    const { versionId } = await seedCatalogAndVersion();

    const draftInput: CreateAiDeploymentInput = {
      workspaceId,
      systemVersionId: versionId,
      mode: "ADVISORY_ONLY",
      founderMemberId: founderId,
      technicalOwnerMemberId: technicalOwnerId,
    };

    const deployment = await createAiDeployment(draftInput);
    expect(deployment.status).toBe("DRAFT");

    const assessment = await submitAiAssessment({
      workspaceId,
      deploymentId: deployment.id,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "private-business advisory",
      controls: ["HUMAN_CONFIRMATION", "DATA_GATE"],
      expiresAt: "2027-01-01T00:00:00Z",
    });
    expect(assessment.status).toBe("PENDING");

    // Seed evidence and profiles required for activation
    const evidenceId = generateSnowflake();
    await db.insert(aiComplianceEvidence).values({
      id: evidenceId,
      workspaceId: BigInt(workspaceId),
      assessmentId: BigInt(assessment.id),
      evidenceType: "ARCHITECTURE_REVIEW",
      uriReference: "vault://evidence/arch-rev-1",
      contentHash: "sha256:evidence123",
      reviewerMemberId: BigInt(founderId),
    });

    await seedApprovedProviderAndDataProfile(workspaceId, deployment.id);

    // Attempt approval by technical owner instead of Founder -> fails
    await expect(
      approveAiAssessment({
        deploymentId: deployment.id,
        assessmentId: assessment.id,
        approvedByMemberId: technicalOwnerId,
        rationale: "ship",
        expiresAt: "2027-01-01T00:00:00Z",
      })
    ).rejects.toMatchObject({ code: "FOUNDER_APPROVAL_REQUIRED" });

    // Approval by Founder succeeds
    const approved = await approveAiAssessment({
      deploymentId: deployment.id,
      assessmentId: assessment.id,
      approvedByMemberId: founderId,
      rationale: "Approved by Founder after review",
      expiresAt: "2027-01-01T00:00:00Z",
    });
    expect(approved.status).toBe("APPROVED_FOR_USE");

    const reloaded = await getDeployment(deployment.id);
    expect(reloaded.status).toBe("APPROVED_FOR_USE");
    expect(reloaded.currentAssessmentId).toBe(assessment.id);
  });

  it("handles suspend and resume lifecycle transitions", async () => {
    const ws2 = String(generateSnowflake());
    const founder2 = String(generateSnowflake());
    const techOwner2 = String(generateSnowflake());

    const { versionId } = await seedCatalogAndVersion();
    const deployment = await createAiDeployment({
      workspaceId: ws2,
      systemVersionId: versionId,
      mode: "ADVISORY_ONLY",
      founderMemberId: founder2,
      technicalOwnerMemberId: techOwner2,
    });

    const assessment = await submitAiAssessment({
      workspaceId: ws2,
      deploymentId: deployment.id,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "private-business advisory",
      controls: ["HUMAN_CONFIRMATION"],
      expiresAt: "2027-01-01T00:00:00Z",
    });

    await seedApprovedProviderAndDataProfile(ws2, deployment.id);

    const evidenceId = generateSnowflake();
    await db.insert(aiComplianceEvidence).values({
      id: evidenceId,
      workspaceId: BigInt(ws2),
      assessmentId: BigInt(assessment.id),
      evidenceType: "POLICY_GATE",
      uriReference: "vault://evidence/policy-1",
      contentHash: "sha256:pol123",
      reviewerMemberId: BigInt(founder2),
    });

    await approveAiAssessment({
      deploymentId: deployment.id,
      assessmentId: assessment.id,
      approvedByMemberId: founder2,
      rationale: "Founder approves deployment",
      expiresAt: "2027-01-01T00:00:00Z",
    });

    // Suspend
    const suspended = await suspendAiDeployment({
      deploymentId: deployment.id,
      rationale: "Emergency security audit",
      suspendedByMemberId: founder2,
    });
    expect(suspended.status).toBe("SUSPENDED");

    // Resume requires Founder
    await expect(
      resumeAiDeployment({
        deploymentId: deployment.id,
        rationale: "Resolved by tech owner",
        resumedByMemberId: techOwner2,
      })
    ).rejects.toMatchObject({ code: "FOUNDER_APPROVAL_REQUIRED" });

    const resumed = await resumeAiDeployment({
      deploymentId: deployment.id,
      rationale: "Resolved audit, Founder resumes",
      resumedByMemberId: founder2,
    });
    expect(resumed.status).toBe("APPROVED_FOR_USE");
  });

  it("returns no deployment from another workspace", async () => {
    await expect(getComplianceCenterView(otherWorkspaceId)).resolves.toMatchObject({
      deployments: [],
    });
  });
});
