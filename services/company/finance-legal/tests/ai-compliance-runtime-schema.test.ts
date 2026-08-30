import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const {
  aiSystemCatalog,
  aiSystemVersions,
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceEvidence,
  aiProviderProfiles,
  aiDataProcessingProfiles,
  aiIncidents,
  aiIncidentActions,
  aiComplianceSnapshots,
} = schema;

/**
 * Regression DB cho defense-in-depth ở tầng PostgreSQL (Task 2): composite
 * unique key (workspace_id, id) trên các bảng cha thuộc workspace + composite
 * FK (workspace_id, <ref>_id) trên bảng con. Mục tiêu: PostgreSQL tự chặn
 * insert cross-workspace, không chỉ dựa vào scoping ở tầng code TS (Task 1).
 *
 * Mỗi test dựng một parent hợp lệ ở workspace A, rồi cố insert một child row
 * khai workspace_id = B nhưng trỏ tới parent id thuộc workspace A — insert
 * đó phải bị PostgreSQL từ chối (composite FK vi phạm).
 */
describe("AI compliance runtime schema — database-level workspace ownership", () => {
  async function seedSystemVersion() {
    const catalogId = generateSnowflake();
    const versionId = generateSnowflake();

    await db.insert(aiSystemCatalog).values({
      id: catalogId,
      systemKey: `runtime-schema-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: "Runtime Schema Test System",
      allowedPurposes: ["advisory"],
      prohibitedPurposes: [],
      lifecycleStatus: "ACTIVE",
    });

    await db.insert(aiSystemVersions).values({
      id: versionId,
      systemCatalogId: catalogId,
      version: "1.0.0",
      configHash: `sha256:runtime-schema-${Date.now()}`,
      status: "ACTIVE",
    });

    return versionId;
  }

  async function seedDeployment(workspaceId: bigint) {
    const systemVersionId = await seedSystemVersion();
    const deploymentId = generateSnowflake();

    await db.insert(workspaceAiDeployments).values({
      id: deploymentId,
      workspaceId,
      systemVersionId,
      mode: "ADVISORY_ONLY",
      status: "DRAFT",
      founderMemberId: generateSnowflake(),
    });

    return deploymentId;
  }

  async function seedAssessment(workspaceId: bigint, deploymentId: bigint) {
    const assessmentId = generateSnowflake();

    await db.insert(aiRiskAssessments).values({
      id: assessmentId,
      workspaceId,
      deploymentId,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "runtime-schema-test",
      controls: ["HUMAN_CONFIRMATION"],
      expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
    });

    return assessmentId;
  }

  async function seedIncident(workspaceId: bigint, deploymentId: bigint) {
    const incidentId = generateSnowflake();

    await db.insert(aiIncidents).values({
      id: incidentId,
      workspaceId,
      deploymentId,
      severity: "LOW",
      status: "OPEN",
      detectedAt: new Date(),
      summary: "runtime-schema-test",
    });

    return incidentId;
  }

  async function seedProviderProfile(workspaceId: bigint) {
    const providerProfileId = generateSnowflake();

    await db.insert(aiProviderProfiles).values({
      id: providerProfileId,
      workspaceId,
      providerKey: "deepseek",
      modelKey: "deepseek-chat",
      version: `v${Date.now()}`,
      status: "APPROVED",
      declaredProcessingRegion: "SG",
      allowedDataCategories: ["BUSINESS_CONFIDENTIAL"],
    });

    return providerProfileId;
  }

  it("rejects an ai_risk_assessments row that combines workspace B with a deployment owned by workspace A", async () => {
    const workspaceA = generateSnowflake();
    const workspaceB = generateSnowflake();
    const deploymentA = await seedDeployment(workspaceA);

    await expect(
      db.insert(aiRiskAssessments).values({
        id: generateSnowflake(),
        workspaceId: workspaceB,
        deploymentId: deploymentA,
        classification: "OUT_OF_CATALOG",
        intendedPurpose: "cross-workspace-attempt",
        controls: [],
        expiresAt: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
      })
    ).rejects.toThrow();
  });

  it("rejects a data processing profile that combines workspace B with a deployment owned by workspace A", async () => {
    const workspaceA = generateSnowflake();
    const workspaceB = generateSnowflake();
    const deploymentA = await seedDeployment(workspaceA);

    await expect(
      db.insert(aiDataProcessingProfiles).values({
        id: generateSnowflake(),
        workspaceId: workspaceB,
        deploymentId: deploymentA,
        purposeId: "cross-workspace-attempt",
        dataCategories: [],
        retentionPolicyId: "retention-30d",
        version: "v1",
        status: "DRAFT",
      })
    ).rejects.toThrow();
  });

  it("rejects a data processing profile whose recipient provider profile belongs to another workspace", async () => {
    const workspaceA = generateSnowflake();
    const workspaceB = generateSnowflake();
    const deploymentB = await seedDeployment(workspaceB);
    const providerProfileA = await seedProviderProfile(workspaceA);

    await expect(
      db.insert(aiDataProcessingProfiles).values({
        id: generateSnowflake(),
        workspaceId: workspaceB,
        deploymentId: deploymentB,
        recipientProviderProfileId: providerProfileA,
        purposeId: "cross-workspace-attempt",
        dataCategories: [],
        retentionPolicyId: "retention-30d",
        version: "v1",
        status: "DRAFT",
      })
    ).rejects.toThrow();
  });

  it("rejects compliance evidence that combines workspace B with an assessment owned by workspace A", async () => {
    const workspaceA = generateSnowflake();
    const workspaceB = generateSnowflake();
    const deploymentA = await seedDeployment(workspaceA);
    const assessmentA = await seedAssessment(workspaceA, deploymentA);

    await expect(
      db.insert(aiComplianceEvidence).values({
        id: generateSnowflake(),
        workspaceId: workspaceB,
        assessmentId: assessmentA,
        evidenceType: "ARCHITECTURE_REVIEW",
        uriReference: "vault://evidence/cross-workspace",
        contentHash: "sha256:cross-workspace",
        reviewerMemberId: generateSnowflake(),
      })
    ).rejects.toThrow();
  });

  it("rejects an incident that combines workspace B with a deployment owned by workspace A", async () => {
    const workspaceA = generateSnowflake();
    const workspaceB = generateSnowflake();
    const deploymentA = await seedDeployment(workspaceA);

    await expect(
      db.insert(aiIncidents).values({
        id: generateSnowflake(),
        workspaceId: workspaceB,
        deploymentId: deploymentA,
        severity: "LOW",
        status: "OPEN",
        detectedAt: new Date(),
        summary: "cross-workspace-attempt",
      })
    ).rejects.toThrow();
  });

  it("rejects an incident action that combines workspace B with an incident owned by workspace A", async () => {
    const workspaceA = generateSnowflake();
    const workspaceB = generateSnowflake();
    const deploymentA = await seedDeployment(workspaceA);
    const incidentA = await seedIncident(workspaceA, deploymentA);

    await expect(
      db.insert(aiIncidentActions).values({
        id: generateSnowflake(),
        workspaceId: workspaceB,
        incidentId: incidentA,
        actionType: "CONTAINMENT",
        description: "cross-workspace-attempt",
        takenByMemberId: generateSnowflake(),
      })
    ).rejects.toThrow();
  });

  it("rejects a compliance snapshot that combines workspace B with a deployment owned by workspace A", async () => {
    const workspaceA = generateSnowflake();
    const workspaceB = generateSnowflake();
    const deploymentA = await seedDeployment(workspaceA);
    const assessmentB = await seedAssessment(workspaceB, await seedDeployment(workspaceB));

    await expect(
      db.insert(aiComplianceSnapshots).values({
        id: generateSnowflake(),
        workspaceId: workspaceB,
        deploymentId: deploymentA,
        assessmentId: assessmentB,
        mode: "ADVISORY_ONLY",
        status: "DRAFT",
        allowedCapabilities: [],
        providerProfileVersion: "1.0.0",
        dataProfileVersion: "1.0.0",
        legalVersionIds: [],
        policySnapshotHash: "sha256:cross-workspace",
        snapshotHash: `sha256:cross-workspace-${Date.now()}`,
        expiresAt: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000),
      })
    ).rejects.toThrow();
  });

  it("rejects a compliance snapshot that combines workspace B with an assessment owned by workspace A", async () => {
    const workspaceA = generateSnowflake();
    const workspaceB = generateSnowflake();
    const deploymentA = await seedDeployment(workspaceA);
    const assessmentA = await seedAssessment(workspaceA, deploymentA);
    const deploymentB = await seedDeployment(workspaceB);

    await expect(
      db.insert(aiComplianceSnapshots).values({
        id: generateSnowflake(),
        workspaceId: workspaceB,
        deploymentId: deploymentB,
        assessmentId: assessmentA,
        mode: "ADVISORY_ONLY",
        status: "DRAFT",
        allowedCapabilities: [],
        providerProfileVersion: "1.0.0",
        dataProfileVersion: "1.0.0",
        legalVersionIds: [],
        policySnapshotHash: "sha256:cross-workspace-2",
        snapshotHash: `sha256:cross-workspace-2-${Date.now()}`,
        expiresAt: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000),
      })
    ).rejects.toThrow();
  });

  it("rejects a deployment whose current_assessment_id points to an assessment owned by another workspace", async () => {
    const workspaceA = generateSnowflake();
    const workspaceB = generateSnowflake();
    const deploymentA = await seedDeployment(workspaceA);
    const deploymentB = await seedDeployment(workspaceB);
    const assessmentA = await seedAssessment(workspaceA, deploymentA);

    await expect(
      db
        .update(workspaceAiDeployments)
        .set({ currentAssessmentId: assessmentA })
        .where(eq(workspaceAiDeployments.id, deploymentB))
    ).rejects.toThrow();
  });

  it("still allows a same-workspace parent/child chain to be created", async () => {
    const workspaceId = generateSnowflake();
    const deploymentId = await seedDeployment(workspaceId);
    const assessmentId = await seedAssessment(workspaceId, deploymentId);

    const [evidence] = await db
      .insert(aiComplianceEvidence)
      .values({
        id: generateSnowflake(),
        workspaceId,
        assessmentId,
        evidenceType: "ARCHITECTURE_REVIEW",
        uriReference: "vault://evidence/same-workspace",
        contentHash: "sha256:same-workspace",
        reviewerMemberId: generateSnowflake(),
      })
      .returning();

    expect(evidence.assessmentId).toBe(assessmentId);
  });
});
