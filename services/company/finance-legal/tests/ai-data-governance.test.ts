import { describe, expect, it } from "vitest";
import {
  upsertProviderProfile,
  upsertDataProcessingProfile,
  grantProcessingAuthorization,
  withdrawProcessingAuthorization,
  createDataSubjectRequest,
  resolveDataUse,
  type ResolveDataUseInput,
  type GrantProcessingAuthorizationInput,
} from "../services/ai-data-governance.service";
import { createAiDeployment } from "../services/ai-compliance-governance.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { aiSystemCatalog, aiSystemVersions } = schema;

describe("AI data governance service", () => {
  const workspaceId = String(generateSnowflake());
  const founderId = String(generateSnowflake());

  async function setupWorkspaceAndDeployment() {
    const wsId = String(generateSnowflake());
    const catalogId = generateSnowflake();
    const versionId = generateSnowflake();

    await db.insert(aiSystemCatalog).values({
      id: catalogId,
      systemKey: `cosa-system-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: "COSA System",
      allowedPurposes: ["advisory"],
      prohibitedPurposes: ["automated hiring"],
      lifecycleStatus: "ACTIVE",
    });

    await db.insert(aiSystemVersions).values({
      id: versionId,
      systemCatalogId: catalogId,
      version: "1.0.0",
      configHash: "sha256:cfg123",
      status: "ACTIVE",
    });

    const deployment = await createAiDeployment({
      workspaceId: wsId,
      systemVersionId: String(versionId),
      mode: "ADVISORY_ONLY",
      founderMemberId: founderId,
    });

    const provider = await upsertProviderProfile({
      workspaceId: wsId,
      providerKey: "deepseek",
      modelKey: "deepseek-chat",
      version: "v3",
      status: "APPROVED",
      declaredProcessingRegion: "SG",
      dpaReference: "dpa://legal/2026",
      allowedDataCategories: ["PERSONAL", "BUSINESS_CONFIDENTIAL"],
      reviewedByMemberId: founderId,
    });

    const processingProfile = await upsertDataProcessingProfile({
      workspaceId: wsId,
      deploymentId: String(deployment.id),
      purposeId: "business-advisory",
      dataCategories: ["PERSONAL", "BUSINESS_CONFIDENTIAL"],
      recipientProviderProfileId: String(provider.id),
      retentionPolicyId: "retention-30d",
      version: "v1",
      status: "ACTIVE",
      minimizationRequired: true,
    });

    return {
      wsId,
      deploymentId: String(deployment.id),
      providerProfileId: String(provider.id),
      processingProfileId: String(processingProfile.id),
    };
  }

  it("denies a provider call after authorization is withdrawn", async () => {
    const { wsId, deploymentId } = await setupWorkspaceAndDeployment();

    const activeAuthorization: GrantProcessingAuthorizationInput = {
      workspaceId: wsId,
      subjectReference: "contact_user_999",
      purposeId: "business-advisory",
      purposeVersion: "v1",
      authorityType: "CONSENT",
      proofReference: "vault://proof/consent-999",
    };

    const authRecord = await grantProcessingAuthorization(activeAuthorization);
    expect(authRecord.status).toBe("GRANTED");

    const activeDataUse: ResolveDataUseInput = {
      workspaceId: wsId,
      deploymentId,
      capabilityId: "model.input",
      purposeId: "business-advisory",
      dataCategories: ["PERSONAL"],
      providerKey: "deepseek",
      subjectReference: "contact_user_999",
    };

    // First check should be allowed
    const initialDecision = await resolveDataUse(activeDataUse);
    expect(initialDecision.allowed).toBe(true);
    expect(initialDecision.denialCode).toBeNull();
    expect(initialDecision.minimizationRequired).toBe(true);

    // Withdraw authorization
    await withdrawProcessingAuthorization(wsId, String(authRecord.id), founderId);

    // Subsequent resolution should be denied
    await expect(resolveDataUse(activeDataUse)).resolves.toMatchObject({
      allowed: false,
      denialCode: "PROCESSING_AUTHORIZATION_WITHDRAWN",
    });
  });

  it("stores only a hash for subject reference", async () => {
    const { wsId } = await setupWorkspaceAndDeployment();

    const row = await grantProcessingAuthorization({
      workspaceId: wsId,
      subjectReference: "contact_123",
      purposeId: "business-advisory",
      purposeVersion: "v1",
      authorityType: "CONSENT",
      proofReference: "vault://proof/abc",
    });

    expect(row.subjectReferenceHash).not.toEqual("contact_123");
    expect(row.subjectReferenceHash).toMatch(/^[a-f0-9]{64}$/);
    const serialized = JSON.stringify(row, (_k, v) => (typeof v === "bigint" ? v.toString() : v));
    expect(serialized).not.toContain("contact_123");
  });

  it("denies provider call when provider is not approved for data category", async () => {
    const { wsId, deploymentId } = await setupWorkspaceAndDeployment();

    const decision = await resolveDataUse({
      workspaceId: wsId,
      deploymentId,
      purposeId: "business-advisory",
      dataCategories: ["SENSITIVE_PERSONAL"], // provider only allows PERSONAL & BUSINESS_CONFIDENTIAL
      providerKey: "deepseek",
    });

    expect(decision.allowed).toBe(false);
    expect(decision.denialCode).toBe("PROVIDER_CATEGORY_NOT_PERMITTED");
  });

  it("denies personal data without subject reference", async () => {
    const { wsId, deploymentId } = await setupWorkspaceAndDeployment();

    const decision = await resolveDataUse({
      workspaceId: wsId,
      deploymentId,
      purposeId: "business-advisory",
      dataCategories: ["PERSONAL"],
      providerKey: "deepseek",
      // subjectReference is missing
    });

    expect(decision.allowed).toBe(false);
    expect(decision.denialCode).toBe("PROCESSING_AUTHORIZATION_MISSING");
  });

  it("denies provider profile that excludes requested model", async () => {
    const { wsId, deploymentId } = await setupWorkspaceAndDeployment();

    const decision = await resolveDataUse({
      workspaceId: wsId,
      deploymentId,
      purposeId: "business-advisory",
      dataCategories: ["BUSINESS_CONFIDENTIAL"],
      providerKey: "deepseek",
      modelKey: "unapproved-model-v99",
    });

    expect(decision.allowed).toBe(false);
    expect(decision.denialCode).toBe("MODEL_NOT_APPROVED");
  });
});
