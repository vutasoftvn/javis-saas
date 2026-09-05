import { describe, expect, it } from "vitest";
import {
  createAiDeployment,
  submitAiAssessment,
  approveAiAssessment,
  getComplianceCenterView,
  type CreateAiDeploymentInput,
} from "../services/ai-compliance-governance.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import type { TenantContext } from "../../shared/types/tenant_context";

const {
  aiSystemCatalog,
  aiSystemVersions,
  aiProviderProfiles,
  aiDataProcessingProfiles,
  aiComplianceEvidence,
  legalEntityProfiles,
  workspaceAiDeployments,
} = schema;

describe("deployment-authority (F16)", () => {
  async function seedCatalogAndVersion() {
    const catalogId = generateSnowflake();
    const versionId = generateSnowflake();

    await db.insert(aiSystemCatalog).values({
      id: catalogId,
      systemKey: `auth-advisory-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: "Authorized AI Agent",
      allowedPurposes: ["business advisory"],
      prohibitedPurposes: ["unlawful actions"],
      lifecycleStatus: "ACTIVE",
    });

    await db.insert(aiSystemVersions).values({
      id: versionId,
      systemCatalogId: catalogId,
      version: "1.0.0",
      configHash: "sha256:auth123",
      status: "ACTIVE",
    });

    return { versionId: String(versionId) };
  }

  async function seedApprovedProviderAndDataProfile(wsId: string, deploymentId: string | bigint) {
    const providerProfileId = generateSnowflake();
    const dataProfileId = generateSnowflake();

    await db.insert(aiProviderProfiles).values({
      id: providerProfileId,
      workspaceId: BigInt(wsId),
      providerKey: "openai",
      modelKey: "gpt-4o",
      version: "2026",
      status: "APPROVED",
      declaredProcessingRegion: "SG",
      dpaReference: "dpa://auth-test",
      allowedDataCategories: ["BUSINESS_CONFIDENTIAL"],
    });

    await db.insert(aiDataProcessingProfiles).values({
      id: dataProfileId,
      workspaceId: BigInt(wsId),
      deploymentId: BigInt(deploymentId),
      purposeId: "business-advisory",
      dataCategories: ["BUSINESS_CONFIDENTIAL"],
      recipientProviderProfileId: providerProfileId,
      retentionPolicyId: "retention-30d",
      version: "v1",
      status: "ACTIVE",
    });
  }

  it("stores created_by, accountable, reviewer, and approved_by separately with versioning", async () => {
    const wsId = String(generateSnowflake());
    const creatorId = String(generateSnowflake());
    const accountableId = String(generateSnowflake());
    const reviewerId = String(generateSnowflake());
    const approverFounderId = String(generateSnowflake());

    const { versionId } = await seedCatalogAndVersion();

    // 1. Create deployment with explicit creator & accountable
    const deployment = await createAiDeployment({
      workspaceId: wsId,
      systemVersionId: versionId,
      mode: "ADVISORY_ONLY",
      founderMemberId: approverFounderId,
      createdByMemberId: creatorId,
      accountableMemberId: accountableId,
    });

    expect(deployment.status).toBe("DRAFT");
    expect(String(deployment.createdByMemberId)).toBe(creatorId);
    expect(String(deployment.accountableMemberId)).toBe(accountableId);
    expect(deployment.policyVersion).toBeGreaterThanOrEqual(1);

    // 2. Submit assessment with reviewer
    const assessment = await submitAiAssessment({
      workspaceId: wsId,
      deploymentId: deployment.id,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "business advisory",
      controls: ["HUMAN_CONFIRMATION"],
      reviewerMemberId: reviewerId,
      expiresAt: "2027-01-01T00:00:00Z",
    });

    await seedApprovedProviderAndDataProfile(wsId, deployment.id);

    const evidenceId = generateSnowflake();
    await db.insert(aiComplianceEvidence).values({
      id: evidenceId,
      workspaceId: BigInt(wsId),
      assessmentId: BigInt(assessment.id),
      evidenceType: "ARCHITECTURE_REVIEW",
      uriReference: "vault://evidence/1",
      contentHash: "sha256:hash123",
      reviewerMemberId: BigInt(reviewerId),
    });

    // 3. Prevent self-approval when creator attempts to approve without sole proprietorship
    await expect(
      approveAiAssessment({
        workspaceId: wsId,
        deploymentId: deployment.id,
        assessmentId: assessment.id,
        approvedByMemberId: creatorId,
        rationale: "Self approving",
        expiresAt: "2027-01-01T00:00:00Z",
      })
    ).rejects.toMatchObject({ code: "SELF_APPROVAL_PROHIBITED" });

    // 4. Authorized approver approves successfully
    const approved = await approveAiAssessment({
      workspaceId: wsId,
      deploymentId: deployment.id,
      assessmentId: assessment.id,
      approvedByMemberId: approverFounderId,
      rationale: "Founder approves compliant deployment",
      expiresAt: "2027-01-01T00:00:00Z",
    });

    expect(approved.status).toBe("APPROVED_FOR_USE");
    expect(String(approved.approvedByMemberId)).toBe(approverFounderId);
    expect(approved.approvedVersion).toBe(1);

    // 5. Check compliance center view includes authority fields
    const centerView = await getComplianceCenterView(wsId);
    const depView = centerView.deployments.find((d) => d.id === String(deployment.id));
    expect(depView).toBeDefined();
    expect(depView?.createdByMemberId).toBe(creatorId);
    expect(depView?.accountableMemberId).toBe(accountableId);
    expect(depView?.reviewerMemberId).toBe(reviewerId);
    expect(depView?.approvedByMemberId).toBe(approverFounderId);
    expect(depView?.approvedVersion).toBe(1);
  });

  it("permits self-approval when sole proprietorship exemption applies", async () => {
    const wsId = String(generateSnowflake());
    const soleOwnerId = String(generateSnowflake());

    const { versionId } = await seedCatalogAndVersion();

    // Create sole proprietorship entity profile
    await db.insert(legalEntityProfiles).values({
      id: generateSnowflake(),
      workspaceId: BigInt(wsId),
      legalName: "Solo Venture",
      entityType: "SOLE_PROPRIETORSHIP",
      status: "VERIFIED",
    });

    const deployment = await createAiDeployment({
      workspaceId: wsId,
      systemVersionId: versionId,
      mode: "ADVISORY_ONLY",
      founderMemberId: soleOwnerId,
      createdByMemberId: soleOwnerId,
    });

    const assessment = await submitAiAssessment({
      workspaceId: wsId,
      deploymentId: deployment.id,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "business advisory",
      controls: ["HUMAN_CONFIRMATION"],
      expiresAt: "2027-01-01T00:00:00Z",
    });

    await seedApprovedProviderAndDataProfile(wsId, deployment.id);

    await db.insert(aiComplianceEvidence).values({
      id: generateSnowflake(),
      workspaceId: BigInt(wsId),
      assessmentId: BigInt(assessment.id),
      evidenceType: "ARCHITECTURE_REVIEW",
      uriReference: "vault://evidence/sole",
      contentHash: "sha256:sole",
      reviewerMemberId: BigInt(soleOwnerId),
    });

    // Sole owner can self-approve because entity is SOLE_PROPRIETORSHIP
    const approved = await approveAiAssessment({
      workspaceId: wsId,
      deploymentId: deployment.id,
      assessmentId: assessment.id,
      approvedByMemberId: soleOwnerId,
      rationale: "Sole owner self-approval with explicit audit trail",
      expiresAt: "2027-01-01T00:00:00Z",
    });

    expect(approved.status).toBe("APPROVED_FOR_USE");
    expect(String(approved.approvedByMemberId)).toBe(soleOwnerId);
  });

  it("enforces business authorization when ctx is provided", async () => {
    const wsId = String(generateSnowflake());
    const creatorId = String(generateSnowflake());
    const memberWithoutPermId = String(generateSnowflake());

    const { versionId } = await seedCatalogAndVersion();

    const deployment = await createAiDeployment({
      workspaceId: wsId,
      systemVersionId: versionId,
      mode: "ADVISORY_ONLY",
      createdByMemberId: creatorId,
      founderMemberId: generateSnowflake(),
    });

    const assessment = await submitAiAssessment({
      workspaceId: wsId,
      deploymentId: deployment.id,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "business advisory",
      controls: ["HUMAN_CONFIRMATION"],
      expiresAt: "2027-01-01T00:00:00Z",
    });

    await seedApprovedProviderAndDataProfile(wsId, deployment.id);

    await db.insert(aiComplianceEvidence).values({
      id: generateSnowflake(),
      workspaceId: BigInt(wsId),
      assessmentId: BigInt(assessment.id),
      evidenceType: "ARCHITECTURE_REVIEW",
      uriReference: "vault://evidence/perm",
      contentHash: "sha256:perm",
      reviewerMemberId: BigInt(generateSnowflake()),
    });

    // Context for a normal non-founder member with no assigned approve role
    const ctxUnauthorized: TenantContext = {
      workspaceId: wsId,
      userId: memberWithoutPermId,
      workforceMemberId: memberWithoutPermId,
      membershipRole: "member",
    };

    await expect(
      approveAiAssessment(
        {
          workspaceId: wsId,
          deploymentId: deployment.id,
          assessmentId: assessment.id,
          approvedByMemberId: memberWithoutPermId,
          rationale: "Unauthorized approval",
          expiresAt: "2027-01-01T00:00:00Z",
        },
        ctxUnauthorized
      )
    ).rejects.toMatchObject({ code: "PERMISSION_DENIED" });

    // Context for founder succeeds
    const founderId = String(generateSnowflake());
    const ctxFounder: TenantContext = {
      workspaceId: wsId,
      userId: founderId,
      workforceMemberId: founderId,
      membershipRole: "founder",
    };

    const approved = await approveAiAssessment(
      {
        workspaceId: wsId,
        deploymentId: deployment.id,
        assessmentId: assessment.id,
        approvedByMemberId: founderId,
        rationale: "Founder approves with verified authority",
        expiresAt: "2027-01-01T00:00:00Z",
      },
      ctxFounder
    );

    expect(approved.status).toBe("APPROVED_FOR_USE");
    expect(String(approved.approvedByMemberId)).toBe(founderId);
  });
});
