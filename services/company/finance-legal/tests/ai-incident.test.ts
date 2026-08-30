import { describe, expect, it } from "vitest";
import { openAiIncident } from "../services/ai-incident-response.service";
import {
  createAiDeployment,
  submitAiAssessment,
  approveAiAssessment,
  getDeployment,
} from "../services/ai-compliance-governance.service";
import { upsertProviderProfile, upsertDataProcessingProfile } from "../services/ai-data-governance.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { aiSystemCatalog, aiSystemVersions, aiComplianceEvidence } = schema;

describe("AI critical incident suspension", () => {
  async function setupActiveDeployment() {
    const wsId = String(generateSnowflake());
    const founderId = String(generateSnowflake());
    const catalogId = generateSnowflake();
    const versionId = generateSnowflake();

    await db.insert(aiSystemCatalog).values({
      id: catalogId,
      systemKey: `system-inc-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: "Agent System Inc",
      allowedPurposes: ["advisory"],
      prohibitedPurposes: [],
      lifecycleStatus: "ACTIVE",
    });

    await db.insert(aiSystemVersions).values({
      id: versionId,
      systemCatalogId: catalogId,
      version: "1.0.0",
      configHash: "sha256:cfg-inc",
      status: "ACTIVE",
    });

    const deployment = await createAiDeployment({
      workspaceId: wsId,
      systemVersionId: String(versionId),
      mode: "ADVISORY_ONLY",
      founderMemberId: founderId,
    });

    const assessment = await submitAiAssessment({
      workspaceId: wsId,
      deploymentId: String(deployment.id),
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "advisory",
      controls: ["HUMAN_CONFIRMATION"],
      expiresAt: "2027-01-01T00:00:00Z",
    });

    const provider = await upsertProviderProfile({
      workspaceId: wsId,
      providerKey: "deepseek",
      modelKey: "deepseek-chat",
      version: "v3",
      status: "APPROVED",
      declaredProcessingRegion: "SG",
      allowedDataCategories: ["BUSINESS_CONFIDENTIAL"],
      reviewedByMemberId: founderId,
    });

    await upsertDataProcessingProfile({
      workspaceId: wsId,
      deploymentId: String(deployment.id),
      purposeId: "advisory",
      dataCategories: ["BUSINESS_CONFIDENTIAL"],
      recipientProviderProfileId: String(provider.id),
      retentionPolicyId: "retention-30d",
      version: "v1",
      status: "ACTIVE",
    });

    const evidenceId = generateSnowflake();
    await db.insert(aiComplianceEvidence).values({
      id: evidenceId,
      workspaceId: BigInt(wsId),
      assessmentId: BigInt(assessment.id),
      evidenceType: "ARCHITECTURE_REVIEW",
      uriReference: "vault://evidence/1",
      contentHash: "sha256:123",
      reviewerMemberId: BigInt(founderId),
    });

    await approveAiAssessment({
      workspaceId: wsId,
      deploymentId: String(deployment.id),
      assessmentId: String(assessment.id),
      approvedByMemberId: founderId,
      rationale: "Approved",
      expiresAt: "2027-01-01T00:00:00Z",
    });

    return { wsId, founderId, deploymentId: String(deployment.id) };
  }

  it("suspends a deployment when a critical incident opens", async () => {
    const { wsId, deploymentId } = await setupActiveDeployment();

    await openAiIncident({
      workspaceId: wsId,
      deploymentId,
      severity: "CRITICAL",
      detectedAt: "2026-08-29T08:00:00Z",
      dataCategories: ["SENSITIVE_PERSONAL"],
    });

    await expect(getDeployment(wsId, deploymentId)).resolves.toMatchObject({ status: "SUSPENDED" });
  });
});
