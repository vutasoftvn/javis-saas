import { describe, expect, it } from "vitest";
import { eq, and } from "drizzle-orm";
import { createHash } from "node:crypto";
import {
  getDeploymentInWorkspace,
  getAssessmentInWorkspace,
  getComplianceSnapshotInWorkspace,
  getIncidentInWorkspace,
  getProcessingAuthorizationInWorkspace,
} from "../services/ai-compliance-access.service";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { db, schema } from "../models/db";

// Helper functions to compute hashes (same as in ai-data-governance.service.ts)
function hashSubjectReference(subjectRef: string): string {
  return createHash("sha256").update(subjectRef.trim()).digest("hex");
}

function hashProof(proof: string): string {
  return createHash("sha256").update(proof.trim()).digest("hex");
}

const {
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceSnapshots,
  aiIncidents,
  dataProcessingAuthorizations,
  aiSystemVersions,
  aiSystemCatalog,
} = schema;

describe("AI Compliance Access Control", () => {
  async function setupDeploymentAndAssessment() {
    const ws1Id = generateSnowflake();
    const ws2Id = generateSnowflake();
    const versionId = generateSnowflake();
    const catalogId = generateSnowflake();

    // Create system and version
    await db.insert(aiSystemCatalog).values({
      id: catalogId,
      systemKey: `access-test-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: "Access Test System",
      allowedPurposes: ["advisory"],
      prohibitedPurposes: [],
      lifecycleStatus: "ACTIVE",
    });

    await db.insert(aiSystemVersions).values({
      id: versionId,
      systemCatalogId: catalogId,
      version: "1.0.0",
      configHash: "sha256:access-test",
      status: "ACTIVE",
    });

    // Create deployments in different workspaces
    const dep1Id = generateSnowflake();
    const dep2Id = generateSnowflake();

    await db.insert(workspaceAiDeployments).values({
      id: dep1Id,
      workspaceId: ws1Id,
      systemVersionId: versionId,
      mode: "ADVISORY_ONLY",
      status: "APPROVED_FOR_USE",
      founderMemberId: generateSnowflake(),
    });

    await db.insert(workspaceAiDeployments).values({
      id: dep2Id,
      workspaceId: ws2Id,
      systemVersionId: versionId,
      mode: "ADVISORY_ONLY",
      status: "APPROVED_FOR_USE",
      founderMemberId: generateSnowflake(),
    });

    // Create assessments in both deployments
    const assess1Id = generateSnowflake();
    const assess2Id = generateSnowflake();

    await db.insert(aiRiskAssessments).values({
      id: assess1Id,
      workspaceId: ws1Id,
      deploymentId: dep1Id,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "advisory",
      controls: ["HUMAN_CONFIRMATION"],
      status: "APPROVED",
      expiresAt: new Date(Date.now() + 86400000),
    });

    await db.insert(aiRiskAssessments).values({
      id: assess2Id,
      workspaceId: ws2Id,
      deploymentId: dep2Id,
      classification: "OUT_OF_CATALOG",
      intendedPurpose: "advisory",
      controls: ["HUMAN_CONFIRMATION"],
      status: "APPROVED",
      expiresAt: new Date(Date.now() + 86400000),
    });

    return { ws1Id, ws2Id, dep1Id, dep2Id, assess1Id, assess2Id };
  }

  describe("getDeploymentInWorkspace", () => {
    it("returns deployment when it belongs to the workspace", async () => {
      const { ws1Id, dep1Id } = await setupDeploymentAndAssessment();

      const deployment = await getDeploymentInWorkspace(ws1Id, dep1Id);
      expect(deployment).toBeDefined();
      expect(deployment.id).toBe(dep1Id);
      expect(deployment.workspaceId).toBe(ws1Id);
    });

    it("throws notFound when deployment belongs to different workspace", async () => {
      const { ws1Id, ws2Id, dep2Id } = await setupDeploymentAndAssessment();

      await expect(getDeploymentInWorkspace(ws1Id, dep2Id)).rejects.toMatchObject({
        code: "not_found",
      });
    });

    it("throws notFound when deployment does not exist", async () => {
      const ws1Id = generateSnowflake();
      const nonexistentId = generateSnowflake();

      await expect(getDeploymentInWorkspace(ws1Id, nonexistentId)).rejects.toMatchObject({
        code: "not_found",
      });
    });

    it("handles string and bigint workspace/deployment IDs equivalently", async () => {
      const { ws1Id, dep1Id } = await setupDeploymentAndAssessment();

      const byString = await getDeploymentInWorkspace(String(ws1Id), String(dep1Id));
      const byBigInt = await getDeploymentInWorkspace(ws1Id, dep1Id);

      expect(byString.id).toBe(byBigInt.id);
    });
  });

  describe("getAssessmentInWorkspace", () => {
    it("returns assessment when it belongs to workspace and deployment", async () => {
      const { ws1Id, dep1Id, assess1Id } = await setupDeploymentAndAssessment();

      const assessment = await getAssessmentInWorkspace(ws1Id, dep1Id, assess1Id);
      expect(assessment).toBeDefined();
      expect(assessment.id).toBe(assess1Id);
      expect(assessment.workspaceId).toBe(ws1Id);
      expect(assessment.deploymentId).toBe(dep1Id);
    });

    it("throws notFound when assessment belongs to different workspace", async () => {
      const { ws1Id, ws2Id, dep2Id, assess2Id } = await setupDeploymentAndAssessment();

      await expect(
        getAssessmentInWorkspace(ws1Id, dep2Id, assess2Id)
      ).rejects.toMatchObject({
        code: "not_found",
      });
    });

    it("throws notFound when assessment belongs to different deployment", async () => {
      const { ws1Id, dep1Id, dep2Id, assess2Id } = await setupDeploymentAndAssessment();

      await expect(
        getAssessmentInWorkspace(ws1Id, dep1Id, assess2Id)
      ).rejects.toMatchObject({
        code: "not_found",
      });
    });

    it("throws notFound when assessment does not exist", async () => {
      const ws1Id = generateSnowflake();
      const dep1Id = generateSnowflake();
      const nonexistentId = generateSnowflake();

      await expect(
        getAssessmentInWorkspace(ws1Id, dep1Id, nonexistentId)
      ).rejects.toMatchObject({
        code: "not_found",
      });
    });
  });

  describe("getComplianceSnapshotInWorkspace", () => {
    it("returns snapshot when it belongs to the workspace", async () => {
      const { ws1Id, dep1Id, assess1Id } = await setupDeploymentAndAssessment();
      const snapshotId = generateSnowflake();

      await db.insert(aiComplianceSnapshots).values({
        id: snapshotId,
        workspaceId: ws1Id,
        deploymentId: dep1Id,
        assessmentId: assess1Id,
        mode: "ADVISORY_ONLY",
        status: "APPROVED_FOR_USE",
        providerProfileVersion: "v1",
        dataProfileVersion: "v1",
        provenanceComplete: true,
        policySnapshotHash: "sha256:test",
        snapshotHash: `sha256:test-${Date.now()}-${Math.random()}`,
        issuedAt: new Date(),
        expiresAt: new Date(Date.now() + 86400000),
      });

      const snapshot = await getComplianceSnapshotInWorkspace(ws1Id, snapshotId);
      expect(snapshot).toBeDefined();
      expect(snapshot.id).toBe(snapshotId);
      expect(snapshot.workspaceId).toBe(ws1Id);
    });

    it("throws notFound when snapshot belongs to different workspace", async () => {
      const { ws1Id, ws2Id, dep2Id, assess2Id } = await setupDeploymentAndAssessment();
      const snapshotId = generateSnowflake();

      await db.insert(aiComplianceSnapshots).values({
        id: snapshotId,
        workspaceId: ws2Id,
        deploymentId: dep2Id,
        assessmentId: assess2Id,
        mode: "ADVISORY_ONLY",
        status: "APPROVED_FOR_USE",
        providerProfileVersion: "v1",
        dataProfileVersion: "v1",
        provenanceComplete: true,
        policySnapshotHash: "sha256:test",
        snapshotHash: `sha256:test-${Date.now()}-${Math.random()}`,
        issuedAt: new Date(),
        expiresAt: new Date(Date.now() + 86400000),
      });

      await expect(
        getComplianceSnapshotInWorkspace(ws1Id, snapshotId)
      ).rejects.toMatchObject({
        code: "not_found",
      });
    });

    it("throws notFound when snapshot does not exist", async () => {
      const ws1Id = generateSnowflake();
      const nonexistentId = generateSnowflake();

      await expect(
        getComplianceSnapshotInWorkspace(ws1Id, nonexistentId)
      ).rejects.toMatchObject({
        code: "not_found",
      });
    });
  });

  describe("getIncidentInWorkspace", () => {
    it("returns incident when it belongs to the workspace", async () => {
      const { ws1Id, dep1Id } = await setupDeploymentAndAssessment();
      const incidentId = generateSnowflake();

      await db.insert(aiIncidents).values({
        id: incidentId,
        workspaceId: ws1Id,
        deploymentId: dep1Id,
        severity: "HIGH",
        status: "OPEN",
        detectedAt: new Date(),
        summary: "Test incident summary",
      });

      const incident = await getIncidentInWorkspace(ws1Id, incidentId);
      expect(incident).toBeDefined();
      expect(incident.id).toBe(incidentId);
      expect(incident.workspaceId).toBe(ws1Id);
    });

    it("throws notFound when incident belongs to different workspace", async () => {
      const { ws1Id, ws2Id, dep2Id } = await setupDeploymentAndAssessment();
      const incidentId = generateSnowflake();

      await db.insert(aiIncidents).values({
        id: incidentId,
        workspaceId: ws2Id,
        deploymentId: dep2Id,
        severity: "HIGH",
        status: "OPEN",
        detectedAt: new Date(),
        summary: "Test incident summary",
      });

      await expect(
        getIncidentInWorkspace(ws1Id, incidentId)
      ).rejects.toMatchObject({
        code: "not_found",
      });
    });

    it("throws notFound when incident does not exist", async () => {
      const ws1Id = generateSnowflake();
      const nonexistentId = generateSnowflake();

      await expect(
        getIncidentInWorkspace(ws1Id, nonexistentId)
      ).rejects.toMatchObject({
        code: "not_found",
      });
    });
  });

  describe("getProcessingAuthorizationInWorkspace", () => {
    it("returns authorization when it belongs to the workspace", async () => {
      const ws1Id = generateSnowflake();
      const authId = generateSnowflake();
      const subjectRef = "test-subject";
      const proofRef = "proof://test";

      await db.insert(dataProcessingAuthorizations).values({
        id: authId,
        workspaceId: ws1Id,
        subjectReferenceHash: hashSubjectReference(subjectRef),
        purposeId: "advisory",
        purposeVersion: "v1",
        authorityType: "CONSENT",
        proofReference: proofRef,
        proofHash: hashProof(proofRef),
        status: "GRANTED",
        grantedAt: new Date(),
      });

      const auth = await getProcessingAuthorizationInWorkspace(ws1Id, authId);
      expect(auth).toBeDefined();
      expect(auth.id).toBe(authId);
      expect(auth.workspaceId).toBe(ws1Id);
    });

    it("throws notFound when authorization belongs to different workspace", async () => {
      const ws1Id = generateSnowflake();
      const ws2Id = generateSnowflake();
      const authId = generateSnowflake();
      const subjectRef = "test-subject";
      const proofRef = "proof://test";

      await db.insert(dataProcessingAuthorizations).values({
        id: authId,
        workspaceId: ws2Id,
        subjectReferenceHash: hashSubjectReference(subjectRef),
        purposeId: "advisory",
        purposeVersion: "v1",
        authorityType: "CONSENT",
        proofReference: proofRef,
        proofHash: hashProof(proofRef),
        status: "GRANTED",
        grantedAt: new Date(),
      });

      await expect(
        getProcessingAuthorizationInWorkspace(ws1Id, authId)
      ).rejects.toMatchObject({
        code: "not_found",
      });
    });

    it("throws notFound when authorization does not exist", async () => {
      const ws1Id = generateSnowflake();
      const nonexistentId = generateSnowflake();

      await expect(
        getProcessingAuthorizationInWorkspace(ws1Id, nonexistentId)
      ).rejects.toMatchObject({
        code: "not_found",
      });
    });
  });
});
