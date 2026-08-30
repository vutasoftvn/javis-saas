import { describe, expect, it } from "vitest";
import { resolveRuntimeComplianceSnapshot } from "../services/ai-compliance-snapshot.service";
import { resolveDataUse, upsertProviderProfile, upsertDataProcessingProfile } from "../services/ai-data-governance.service";
import { createAiDeployment, submitAiAssessment, approveAiAssessment, suspendAiDeployment } from "../services/ai-compliance-governance.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { db, schema } from "../models/db";

const {
  aiSystemCatalog,
  aiSystemVersions,
  aiSystemCapabilityBindings,
  aiComplianceEvidence,
} = schema;

describe("AI Compliance Private Contract & Negative Matrix", () => {
  async function seedFullSetup() {
    const wsId = String(generateSnowflake());
    const founderId = String(generateSnowflake());
    const catalogId = generateSnowflake();
    const versionId = generateSnowflake();
    const systemKey = `system-contract-${Date.now()}-${Math.random().toString(36).slice(2)}`;

    await db.insert(aiSystemCatalog).values({
      id: catalogId,
      systemKey,
      name: "Compliance Contract Test",
      allowedPurposes: ["advisory"],
      prohibitedPurposes: [],
      lifecycleStatus: "ACTIVE",
    });

    await db.insert(aiSystemVersions).values({
      id: versionId,
      systemCatalogId: catalogId,
      version: "1.0.0",
      configHash: "sha256:contract-cfg",
      status: "ACTIVE",
    });

    const bindingId = generateSnowflake();
    await db.insert(aiSystemCapabilityBindings).values({
      id: bindingId,
      systemVersionId: versionId,
      capabilityId: "operations.task.list",
      effectClass: "DRAFT",
      decisionDomain: "OPERATIONS",
      requiresHumanConfirmation: true,
      maySendToModel: false,
      maxDataCategory: "BUSINESS_CONFIDENTIAL",
      prohibitedPurpose: false,
    });

    const deployment = await createAiDeployment({
      workspaceId: wsId,
      systemVersionId: String(versionId),
      mode: "ADVISORY_ONLY",
      founderMemberId: founderId,
    });

    const assessment = await submitAiAssessment({
      workspaceId: wsId,
      deploymentId: deployment.id,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "advisory",
      controls: ["HUMAN_CONFIRMATION"],
      expiresAt: new Date(Date.now() + 86400000).toISOString(),
    });

    const evidenceId = generateSnowflake();
    await db.insert(aiComplianceEvidence).values({
      id: evidenceId,
      workspaceId: BigInt(wsId),
      assessmentId: BigInt(assessment.id),
      evidenceType: "ARCHITECTURE_REVIEW",
      uriReference: "vault://evidence/test-contract",
      contentHash: "sha256:evidence-contract",
      reviewerMemberId: BigInt(founderId),
    });

    const provider = await upsertProviderProfile({
      workspaceId: wsId,
      providerKey: "deepseek",
      modelKey: "deepseek-chat",
      version: "v3",
      status: "APPROVED",
      declaredProcessingRegion: "SG",
      dpaReference: "dpa://legal/contract",
      allowedDataCategories: ["BUSINESS_CONFIDENTIAL"],
      reviewedByMemberId: founderId,
    });

    const dataProfile = await upsertDataProcessingProfile({
      workspaceId: wsId,
      deploymentId: String(deployment.id),
      purposeId: "advisory",
      dataCategories: ["BUSINESS_CONFIDENTIAL"],
      recipientProviderProfileId: String(provider.id),
      retentionPolicyId: "retention-30d",
      version: "v1",
      status: "ACTIVE",
    });

    await approveAiAssessment({
      workspaceId: wsId,
      deploymentId: deployment.id,
      assessmentId: assessment.id,
      approvedByMemberId: founderId,
      rationale: "Approved for contract test",
      expiresAt: new Date(Date.now() + 86400000).toISOString(),
    });

    return {
      wsId,
      founderId,
      systemKey,
      deploymentId: String(deployment.id),
      assessmentId: String(assessment.id),
      providerProfileId: String(provider.id),
      dataProfileId: String(dataProfile.id),
    };
  }

  it("fails-closed with 404 when requested capability is not bound to system version", async () => {
    const { wsId, systemKey } = await seedFullSetup();

    await expect(
      resolveRuntimeComplianceSnapshot({
        workspaceId: wsId,
        runId: "run_test_unbound",
        systemKey,
        capabilityIds: ["operations.unknown.capability"],
        policySnapshotHash: "",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("fails-closed with 404 when cross-workspace tenant queries a foreign deployment", async () => {
    const { systemKey } = await seedFullSetup();
    const foreignWsId = String(generateSnowflake());

    await expect(
      resolveRuntimeComplianceSnapshot({
        workspaceId: foreignWsId,
        runId: "run_test_foreign",
        systemKey,
        capabilityIds: ["operations.task.list"],
        policySnapshotHash: "",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });

  it("denies data use when cross-workspace deploymentId is provided", async () => {
    const { deploymentId } = await seedFullSetup();
    const foreignWsId = String(generateSnowflake());

    const decision = await resolveDataUse({
      workspaceId: foreignWsId,
      deploymentId,
      purposeId: "advisory",
      dataCategories: ["BUSINESS_CONFIDENTIAL"],
      providerKey: "deepseek",
    });

    expect(decision.allowed).toBe(false);
    expect(decision.denialCode).toBe("DEPLOYMENT_NOT_FOUND");
  });

  it("denies data use when requested model does not match approved provider profile", async () => {
    const { wsId, deploymentId } = await seedFullSetup();

    const decision = await resolveDataUse({
      workspaceId: wsId,
      deploymentId,
      purposeId: "advisory",
      dataCategories: ["BUSINESS_CONFIDENTIAL"],
      providerKey: "deepseek",
      modelKey: "unapproved-model-xyz",
    });

    expect(decision.allowed).toBe(false);
    expect(decision.denialCode).toBe("MODEL_NOT_APPROVED");
  });

  it("denies runtime snapshot resolution after deployment is suspended", async () => {
    const { wsId, systemKey, deploymentId, founderId } = await seedFullSetup();

    // Verify initially allowed
    const initial = await resolveRuntimeComplianceSnapshot({
      workspaceId: wsId,
      runId: "run_before_suspension",
      systemKey,
      capabilityIds: ["operations.task.list"],
      policySnapshotHash: "",
    });
    expect(initial.status).toBe("APPROVED_FOR_USE");
    expect(initial).toMatchObject({
      providerKey: "deepseek",
      modelKey: "deepseek-chat",
      purposeId: "advisory",
      retentionPolicyId: "retention-30d",
    });

    // Suspend deployment
    await suspendAiDeployment({
      workspaceId: wsId,
      deploymentId,
      rationale: "Emergency audit",
      suspendedByMemberId: founderId,
    });

    // Subsequent resolution must fail closed
    await expect(
      resolveRuntimeComplianceSnapshot({
        workspaceId: wsId,
        runId: "run_after_suspension",
        systemKey,
        capabilityIds: ["operations.task.list"],
        policySnapshotHash: "",
      })
    ).rejects.toMatchObject({ code: "not_found" });
  });
});
