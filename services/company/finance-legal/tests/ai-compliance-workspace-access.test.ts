import { describe, expect, it } from "vitest";
import {
  createAiDeployment,
  submitAiAssessment,
  approveAiAssessment,
  suspendAiDeployment,
  getDeployment,
} from "../services/ai-compliance-governance.service";
import {
  captureComplianceSnapshot,
  verifySnapshotIntegrity,
} from "../services/ai-compliance-snapshot.service";
import {
  reportAiIncident,
  resolveAiIncident,
} from "../services/ai-incident-response.service";
import {
  upsertProviderProfile,
  upsertDataProcessingProfile,
  grantProcessingAuthorization,
  withdrawProcessingAuthorization,
} from "../services/ai-data-governance.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { eq } from "drizzle-orm";

const { aiSystemCatalog, aiSystemVersions, aiComplianceEvidence, aiSystemCapabilityBindings } = schema;

/**
 * Hostile-workspace regression suite cho ADR-AI-COMPLIANCE-RUNTIME-001.
 * Mỗi test dựng resource ở workspace A, sau đó cố mutate/verify từ workspace B
 * (một tenant hợp lệ nhưng không sở hữu resource) và khẳng định:
 *  1. Thao tác bị từ chối với 404 (giống hệt ID không tồn tại — không lộ oracle).
 *  2. Resource ở workspace A không bị thay đổi bởi nỗ lực đó.
 */
describe("AI compliance workspace access hardening", () => {
  async function seedCatalogAndVersion() {
    const catalogId = generateSnowflake();
    const versionId = generateSnowflake();

    await db.insert(aiSystemCatalog).values({
      id: catalogId,
      systemKey: `hostile-ws-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: "Hostile WS Test System",
      allowedPurposes: ["advisory"],
      prohibitedPurposes: [],
      lifecycleStatus: "ACTIVE",
    });

    await db.insert(aiSystemVersions).values({
      id: versionId,
      systemCatalogId: catalogId,
      version: "1.0.0",
      configHash: `sha256:hostile-${Date.now()}`,
      status: "ACTIVE",
    });

    return { versionId: String(versionId) };
  }

  async function seedApprovedProviderAndDataProfile(wsId: string, deploymentId: string | bigint) {
    const providerProfileId = generateSnowflake();
    const dataProfileId = generateSnowflake();

    await db.insert(schema.aiProviderProfiles).values({
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

    await db.insert(schema.aiDataProcessingProfiles).values({
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
  }

  async function createApprovedDeployment(workspaceId: string) {
    const founderId = String(generateSnowflake());
    const { versionId } = await seedCatalogAndVersion();

    const deployment = await createAiDeployment({
      workspaceId,
      systemVersionId: versionId,
      mode: "ADVISORY_ONLY",
      founderMemberId: founderId,
    });

    const assessment = await submitAiAssessment({
      workspaceId,
      deploymentId: deployment.id,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "private-business advisory",
      controls: ["HUMAN_CONFIRMATION"],
      expiresAt: "2027-01-01T00:00:00Z",
    });

    const evidenceId = generateSnowflake();
    await db.insert(aiComplianceEvidence).values({
      id: evidenceId,
      workspaceId: BigInt(workspaceId),
      assessmentId: BigInt(assessment.id),
      evidenceType: "ARCHITECTURE_REVIEW",
      uriReference: "vault://evidence/hostile-ws-1",
      contentHash: "sha256:hostilews123",
      reviewerMemberId: BigInt(founderId),
    });

    await seedApprovedProviderAndDataProfile(workspaceId, deployment.id);

    const approved = await approveAiAssessment({
      workspaceId,
      deploymentId: deployment.id,
      assessmentId: assessment.id,
      approvedByMemberId: founderId,
      rationale: "Approved by Founder after review",
      expiresAt: "2027-01-01T00:00:00Z",
    });

    return { deployment: approved, founderId, assessmentId: String(assessment.id) };
  }

  it("does not mutate a deployment owned by another workspace", async () => {
    const workspaceA = String(generateSnowflake());
    const workspaceB = String(generateSnowflake());
    const founderB = String(generateSnowflake());

    const { deployment } = await createApprovedDeployment(workspaceA);

    await expect(
      suspendAiDeployment({
        workspaceId: workspaceB,
        deploymentId: deployment.id,
        rationale: "attempt",
        suspendedByMemberId: founderB,
      })
    ).rejects.toMatchObject({ code: "not_found" });

    const reloaded = await getDeployment(workspaceA, deployment.id);
    expect(reloaded.status).toBe("APPROVED_FOR_USE");
  });

  it("does not approve an assessment owned by another workspace", async () => {
    const workspaceA = String(generateSnowflake());
    const workspaceB = String(generateSnowflake());
    const founderId = String(generateSnowflake());
    const { versionId } = await seedCatalogAndVersion();

    const deployment = await createAiDeployment({
      workspaceId: workspaceA,
      systemVersionId: versionId,
      mode: "ADVISORY_ONLY",
      founderMemberId: founderId,
    });

    const assessment = await submitAiAssessment({
      workspaceId: workspaceA,
      deploymentId: deployment.id,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "private-business advisory",
      controls: ["HUMAN_CONFIRMATION"],
      expiresAt: "2027-01-01T00:00:00Z",
    });

    await expect(
      approveAiAssessment({
        workspaceId: workspaceB,
        deploymentId: deployment.id,
        assessmentId: assessment.id,
        approvedByMemberId: founderId,
        rationale: "cross-workspace attempt",
        expiresAt: "2027-01-01T00:00:00Z",
      })
    ).rejects.toMatchObject({ code: "not_found" });

    const reloaded = await getDeployment(workspaceA, deployment.id);
    expect(reloaded.status).toBe("ASSESSED");
  });

  it("does not verify (or leak) a compliance snapshot owned by another workspace", async () => {
    const workspaceA = String(generateSnowflake());
    const workspaceB = String(generateSnowflake());

    // Task 4: captureComplianceSnapshot không còn tự tạo deployment/assessment
    // mặc định — phải seed 1 chuỗi approved thật (deployment + assessment +
    // evidence + provider/data profile + capability binding) trước khi gọi.
    const { deployment } = await createApprovedDeployment(workspaceA);
    await db.insert(aiSystemCapabilityBindings).values({
      id: generateSnowflake(),
      systemVersionId: deployment.systemVersionId,
      capabilityId: "draft-legal-memo",
      effectClass: "DRAFT",
      decisionDomain: "LEGAL",
      requiresHumanConfirmation: true,
      maySendToModel: false,
      maxDataCategory: "BUSINESS_CONFIDENTIAL",
      prohibitedPurpose: false,
    });

    const snapshot = await captureComplianceSnapshot(workspaceA, deployment.id);

    await expect(
      verifySnapshotIntegrity(workspaceB, String(snapshot.id))
    ).rejects.toMatchObject({ code: "not_found" });

    // The owning workspace can still verify its own snapshot.
    await expect(verifySnapshotIntegrity(workspaceA, String(snapshot.id))).resolves.toBe(true);
  });

  it("does not resolve an incident owned by another workspace", async () => {
    const workspaceA = String(generateSnowflake());
    const workspaceB = String(generateSnowflake());
    const { deployment, founderId } = await createApprovedDeployment(workspaceA);

    const incident = await reportAiIncident({
      workspaceId: workspaceA,
      deploymentId: deployment.id,
      severity: "LOW",
      incidentType: "DATA_MINIMIZATION_GAP",
      summary: "Minor logging gap",
      reportedByMemberId: founderId,
    });

    await expect(
      resolveAiIncident({
        workspaceId: workspaceB,
        incidentId: incident.id,
        resolvedByMemberId: founderId,
        actionTaken: "cross-workspace attempt",
      })
    ).rejects.toMatchObject({ code: "not_found" });

    const stillOpen = await db
      .select()
      .from(schema.aiIncidents)
      .where(eq(schema.aiIncidents.id, incident.id));
    expect(stillOpen[0].status).toBe("OPEN");
  });

  it("does not withdraw a processing authorization owned by another workspace", async () => {
    const workspaceA = String(generateSnowflake());
    const workspaceB = String(generateSnowflake());
    const founderB = String(generateSnowflake());

    const authRecord = await grantProcessingAuthorization({
      workspaceId: workspaceA,
      subjectReference: "hostile_ws_subject_1",
      purposeId: "business-advisory",
      purposeVersion: "v1",
      authorityType: "CONSENT",
      proofReference: "vault://proof/hostile-ws-1",
    });

    await expect(
      withdrawProcessingAuthorization(workspaceB, String(authRecord.id), founderB)
    ).rejects.toMatchObject({ code: "not_found" });

    const stillGranted = await db
      .select()
      .from(schema.dataProcessingAuthorizations)
      .where(eq(schema.dataProcessingAuthorizations.id, authRecord.id));
    expect(stillGranted[0].status).toBe("GRANTED");
  });
});
