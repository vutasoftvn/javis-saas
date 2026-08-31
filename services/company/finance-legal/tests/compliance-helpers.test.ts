import { describe, expect, it } from "vitest";
import { eq, and } from "drizzle-orm";
import {
  canonicalJsonStringify,
  computeCanonicalSha256,
} from "../services/compliance/canonical-hasher";
import {
  validateApprovedDeployment,
  validateApprovedAssessment,
  validateEvidenceAndProfiles,
  validateCapabilityBindings,
  failCompliance,
} from "../services/compliance/compliance-precondition-validator";
import {
  getSystemKeyForVersion,
  findDeploymentForCapture,
  getDeclaredCapabilityIds,
  insertComplianceSnapshotRecord,
  listComplianceSnapshots,
  findProviderProfileById,
  findRiskAssessmentById,
} from "../services/compliance/compliance-snapshot.repository";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { db, schema } from "../models/db";
import { APIError } from "encore.dev/api";

const {
  aiSystemCatalog,
  aiSystemVersions,
  aiSystemCapabilityBindings,
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceEvidence,
  aiProviderProfiles,
  aiDataProcessingProfiles,
  aiComplianceSnapshots,
} = schema;

describe("Compliance Helpers", () => {
  describe("canonical-hasher", () => {
    it("canonicalJsonStringify produces sorted key order", () => {
      const obj1 = { z: 1, a: 2, m: 3 };
      const obj2 = { a: 2, m: 3, z: 1 };

      const str1 = canonicalJsonStringify(obj1);
      const str2 = canonicalJsonStringify(obj2);

      expect(str1).toBe(str2);
    });

    it("canonicalJsonStringify handles nested objects with key ordering", () => {
      const obj1 = { outer: { z: 1, a: 2 }, top: 3 };
      const obj2 = { top: 3, outer: { a: 2, z: 1 } };

      const str1 = canonicalJsonStringify(obj1);
      const str2 = canonicalJsonStringify(obj2);

      expect(str1).toBe(str2);
    });

    it("canonicalJsonStringify handles arrays", () => {
      const obj1 = { items: [1, 2, 3] };
      const obj2 = { items: [1, 2, 3] };

      const str1 = canonicalJsonStringify(obj1);
      const str2 = canonicalJsonStringify(obj2);

      expect(str1).toBe(str2);
    });

    it("canonicalJsonStringify handles BigInt", () => {
      const obj1 = { id: BigInt("12345") };
      const obj2 = { id: BigInt("12345") };

      const str1 = canonicalJsonStringify(obj1);
      const str2 = canonicalJsonStringify(obj2);

      expect(str1).toBe(str2);
    });

    it("canonicalJsonStringify produces different strings for different values", () => {
      const obj1 = { value: 1 };
      const obj2 = { value: 2 };

      const str1 = canonicalJsonStringify(obj1);
      const str2 = canonicalJsonStringify(obj2);

      expect(str1).not.toBe(str2);
    });

    it("canonicalJsonStringify handles null and primitives", () => {
      expect(canonicalJsonStringify(null)).toBe("null");
      expect(canonicalJsonStringify(true)).toBe("true");
      expect(canonicalJsonStringify("hello")).toBe('"hello"');
      expect(canonicalJsonStringify(42)).toBe("42");
    });

    it("computeCanonicalSha256 produces SHA256 hashes with sha256: prefix", () => {
      const hash = computeCanonicalSha256({ test: "value" });

      expect(hash).toMatch(/^sha256:[a-f0-9]{64}$/);
    });

    it("computeCanonicalSha256 produces same hash for canonically equivalent objects", () => {
      const hash1 = computeCanonicalSha256({ z: 1, a: 2 });
      const hash2 = computeCanonicalSha256({ a: 2, z: 1 });

      expect(hash1).toBe(hash2);
    });

    it("computeCanonicalSha256 produces different hashes for different content", () => {
      const hash1 = computeCanonicalSha256({ value: 1 });
      const hash2 = computeCanonicalSha256({ value: 2 });

      expect(hash1).not.toBe(hash2);
    });
  });

  describe("compliance-snapshot.repository", () => {
    async function setupCompleteChain() {
      const wsId = generateSnowflake();
      const catalogId = generateSnowflake();
      const versionId = generateSnowflake();
      const systemKey = `repo-test-${Date.now()}-${Math.random().toString(36).slice(2)}`;

      await db.insert(aiSystemCatalog).values({
        id: catalogId,
        systemKey,
        name: "Repo Test System",
        allowedPurposes: ["advisory"],
        prohibitedPurposes: [],
        lifecycleStatus: "ACTIVE",
      });

      await db.insert(aiSystemVersions).values({
        id: versionId,
        systemCatalogId: catalogId,
        version: "1.0.0",
        configHash: "sha256:repo-test",
        status: "ACTIVE",
      });

      const bindingId = generateSnowflake();
      await db.insert(aiSystemCapabilityBindings).values({
        id: bindingId,
        systemVersionId: versionId,
        capabilityId: "test.capability",
        effectClass: "READ",
        decisionDomain: "OPERATIONS",
        requiresHumanConfirmation: false,
        maySendToModel: true,
        maxDataCategory: "BUSINESS_CONFIDENTIAL",
        prohibitedPurpose: false,
      });

      const depId = generateSnowflake();
      await db.insert(workspaceAiDeployments).values({
        id: depId,
        workspaceId: wsId,
        systemVersionId: versionId,
        mode: "ADVISORY_ONLY",
        status: "APPROVED_FOR_USE",
        founderMemberId: generateSnowflake(),
      });

      const assessmentId = generateSnowflake();
      await db.insert(aiRiskAssessments).values({
        id: assessmentId,
        workspaceId: wsId,
        deploymentId: depId,
        classification: "OUT_OF_CATALOG",
        intendedPurpose: "advisory",
        controls: ["HUMAN_CONFIRMATION"],
        status: "APPROVED",
        expiresAt: new Date(Date.now() + 86400000),
      });

      const providerProfileId = generateSnowflake();
      await db.insert(aiProviderProfiles).values({
        id: providerProfileId,
        workspaceId: wsId,
        providerKey: "deepseek",
        modelKey: "deepseek-chat",
        version: "v1",
        status: "APPROVED",
        declaredProcessingRegion: "SG",
        allowedDataCategories: ["BUSINESS_CONFIDENTIAL"],
      });

      return {
        wsId,
        catalogId,
        versionId,
        systemKey,
        depId,
        assessmentId,
        providerProfileId,
      };
    }

    it("getSystemKeyForVersion returns the correct system key", async () => {
      const { versionId, systemKey } = await setupCompleteChain();

      const retrievedKey = await getSystemKeyForVersion(versionId);
      expect(retrievedKey).toBe(systemKey);
    });

    it("getSystemKeyForVersion throws notFound for nonexistent version", async () => {
      const nonexistentId = generateSnowflake();

      await expect(getSystemKeyForVersion(nonexistentId)).rejects.toMatchObject({
        code: "not_found",
      });
    });

    it("findDeploymentForCapture returns deployment by ID", async () => {
      const { wsId, depId } = await setupCompleteChain();

      const dep = await findDeploymentForCapture(wsId, depId);
      expect(dep).toBeDefined();
      expect(dep.id).toBe(depId);
    });

    it("findDeploymentForCapture returns latest deployment when no ID provided", async () => {
      const wsId = generateSnowflake();
      const versionId = generateSnowflake();
      const catalogId = generateSnowflake();

      await db.insert(aiSystemCatalog).values({
        id: catalogId,
        systemKey: `latest-test-${Date.now()}`,
        name: "Latest Test",
        allowedPurposes: ["advisory"],
        prohibitedPurposes: [],
        lifecycleStatus: "ACTIVE",
      });

      await db.insert(aiSystemVersions).values({
        id: versionId,
        systemCatalogId: catalogId,
        version: "1.0.0",
        configHash: "sha256:latest",
        status: "ACTIVE",
      });

      const dep1Id = generateSnowflake();
      const dep2Id = generateSnowflake();

      await db.insert(workspaceAiDeployments).values({
        id: dep1Id,
        workspaceId: wsId,
        systemVersionId: versionId,
        mode: "ADVISORY_ONLY",
        status: "APPROVED_FOR_USE",
        founderMemberId: generateSnowflake(),
      });

      // Small delay to ensure different timestamps
      await new Promise((resolve) => setTimeout(resolve, 10));

      await db.insert(workspaceAiDeployments).values({
        id: dep2Id,
        workspaceId: wsId,
        systemVersionId: versionId,
        mode: "ADVISORY_ONLY",
        status: "APPROVED_FOR_USE",
        founderMemberId: generateSnowflake(),
      });

      const latest = await findDeploymentForCapture(wsId);
      expect(latest.id).toBe(dep2Id);
    });

    it("getDeclaredCapabilityIds returns non-prohibited capabilities", async () => {
      const { versionId } = await setupCompleteChain();

      const capIds = await getDeclaredCapabilityIds(versionId);
      expect(capIds).toContain("test.capability");
    });

    it("insertComplianceSnapshotRecord creates a record", async () => {
      const { wsId, depId, assessmentId } = await setupCompleteChain();

      const snapshotId = generateSnowflake();
      const uniqueHash = `sha256:snapshot-${Date.now()}-${Math.random()}`;
      const record = await insertComplianceSnapshotRecord({
        id: snapshotId,
        workspaceId: wsId,
        deploymentId: depId,
        assessmentId,
        mode: "ADVISORY_ONLY",
        status: "APPROVED_FOR_USE",
        providerProfileVersion: "v1",
        dataProfileVersion: "v1",
        provenanceComplete: true,
        policySnapshotHash: "sha256:policy",
        snapshotHash: uniqueHash,
        issuedAt: new Date(),
        expiresAt: new Date(Date.now() + 86400000),
      });

      expect(record).toBeDefined();
      expect(record.id).toBe(snapshotId);
    });

    it("listComplianceSnapshots returns snapshots for workspace", async () => {
      const { wsId, depId, assessmentId } = await setupCompleteChain();

      const snapshotId = generateSnowflake();
      const uniqueHash = `sha256:snapshot-${Date.now()}-${Math.random()}`;
      await db.insert(aiComplianceSnapshots).values({
        id: snapshotId,
        workspaceId: wsId,
        deploymentId: depId,
        assessmentId,
        mode: "ADVISORY_ONLY",
        status: "APPROVED_FOR_USE",
        providerProfileVersion: "v1",
        dataProfileVersion: "v1",
        provenanceComplete: true,
        policySnapshotHash: "sha256:policy",
        snapshotHash: uniqueHash,
        issuedAt: new Date(),
        expiresAt: new Date(Date.now() + 86400000),
      });

      const snapshots = await listComplianceSnapshots(wsId);
      expect(snapshots.length).toBeGreaterThan(0);
      expect(snapshots.some((s) => s.id === snapshotId)).toBe(true);
    });

    it("findProviderProfileById returns profile when it exists", async () => {
      const { providerProfileId } = await setupCompleteChain();

      const profile = await findProviderProfileById(providerProfileId);
      expect(profile).toBeDefined();
      expect(profile.id).toBe(providerProfileId);
    });

    it("findProviderProfileById returns undefined for nonexistent profile", async () => {
      const nonexistentId = generateSnowflake();

      const profile = await findProviderProfileById(nonexistentId);
      expect(profile).toBeUndefined();
    });

    it("findRiskAssessmentById returns assessment when it exists", async () => {
      const { assessmentId } = await setupCompleteChain();

      const assessment = await findRiskAssessmentById(assessmentId);
      expect(assessment).toBeDefined();
      expect(assessment.id).toBe(assessmentId);
    });

    it("findRiskAssessmentById returns undefined for nonexistent assessment", async () => {
      const nonexistentId = generateSnowflake();

      const assessment = await findRiskAssessmentById(nonexistentId);
      expect(assessment).toBeUndefined();
    });
  });

  describe("compliance-precondition-validator", () => {
    async function setupForValidation() {
      const wsId = generateSnowflake();
      const catalogId = generateSnowflake();
      const versionId = generateSnowflake();
      const systemKey = `validator-test-${Date.now()}-${Math.random().toString(36).slice(2)}`;

      await db.insert(aiSystemCatalog).values({
        id: catalogId,
        systemKey,
        name: "Validator Test System",
        allowedPurposes: ["advisory"],
        prohibitedPurposes: [],
        lifecycleStatus: "ACTIVE",
      });

      await db.insert(aiSystemVersions).values({
        id: versionId,
        systemCatalogId: catalogId,
        version: "1.0.0",
        configHash: "sha256:validator",
        status: "ACTIVE",
      });

      const bindingId = generateSnowflake();
      await db.insert(aiSystemCapabilityBindings).values({
        id: bindingId,
        systemVersionId: versionId,
        capabilityId: "allowed.capability",
        effectClass: "READ",
        decisionDomain: "OPERATIONS",
        requiresHumanConfirmation: false,
        maySendToModel: true,
        maxDataCategory: "BUSINESS_CONFIDENTIAL",
        prohibitedPurpose: false,
      });

      // Also add a prohibited capability
      await db.insert(aiSystemCapabilityBindings).values({
        id: generateSnowflake(),
        systemVersionId: versionId,
        capabilityId: "prohibited.capability",
        effectClass: "READ",
        decisionDomain: "OPERATIONS",
        requiresHumanConfirmation: false,
        maySendToModel: true,
        maxDataCategory: "BUSINESS_CONFIDENTIAL",
        prohibitedPurpose: true,
      });

      const depId = generateSnowflake();
      await db.insert(workspaceAiDeployments).values({
        id: depId,
        workspaceId: wsId,
        systemVersionId: versionId,
        mode: "ADVISORY_ONLY",
        status: "APPROVED_FOR_USE",
        founderMemberId: generateSnowflake(),
      });

      const assessmentId = generateSnowflake();
      await db.insert(aiRiskAssessments).values({
        id: assessmentId,
        workspaceId: wsId,
        deploymentId: depId,
        classification: "OUT_OF_CATALOG",
        intendedPurpose: "advisory",
        controls: ["HUMAN_CONFIRMATION"],
        status: "APPROVED",
        expiresAt: new Date(Date.now() + 86400000),
      });

      await db
        .update(workspaceAiDeployments)
        .set({ currentAssessmentId: assessmentId })
        .where(eq(workspaceAiDeployments.id, depId));

      const evidenceId = generateSnowflake();
      await db.insert(aiComplianceEvidence).values({
        id: evidenceId,
        workspaceId: wsId,
        assessmentId,
        evidenceType: "ARCHITECTURE_REVIEW",
        uriReference: "vault://evidence/validator",
        contentHash: "sha256:evidence",
        reviewerMemberId: generateSnowflake(),
      });

      const providerProfileId = generateSnowflake();
      await db.insert(aiProviderProfiles).values({
        id: providerProfileId,
        workspaceId: wsId,
        providerKey: "deepseek",
        modelKey: "deepseek-chat",
        version: "v1",
        status: "APPROVED",
        declaredProcessingRegion: "SG",
        allowedDataCategories: ["BUSINESS_CONFIDENTIAL"],
      });

      const dataProfileId = generateSnowflake();
      await db.insert(aiDataProcessingProfiles).values({
        id: dataProfileId,
        workspaceId: wsId,
        deploymentId: depId,
        purposeId: "advisory",
        dataCategories: ["BUSINESS_CONFIDENTIAL"],
        recipientProviderProfileId: providerProfileId,
        retentionPolicyId: "retention-30d",
        version: "v1",
        status: "ACTIVE",
      });

      return {
        wsId,
        versionId,
        systemKey,
        depId,
        assessmentId,
        providerProfileId,
        dataProfileId,
      };
    }

    it("validateApprovedDeployment succeeds for valid deployment", async () => {
      const { wsId, systemKey } = await setupForValidation();

      const result = await validateApprovedDeployment(wsId, systemKey);
      expect(result.catalog).toBeDefined();
      expect(result.deployment).toBeDefined();
    });

    it("validateApprovedDeployment throws for nonexistent system", async () => {
      const wsId = generateSnowflake();
      const invalidSystemKey = "nonexistent-system";

      await expect(
        validateApprovedDeployment(wsId, invalidSystemKey)
      ).rejects.toThrow();
    });

    it("validateApprovedAssessment succeeds for valid approved assessment", async () => {
      const { wsId, depId } = await setupForValidation();

      const [deployment] = await db
        .select()
        .from(workspaceAiDeployments)
        .where(eq(workspaceAiDeployments.id, depId));

      const assessment = await validateApprovedAssessment(wsId, deployment);
      expect(assessment).toBeDefined();
      expect(assessment.status).toBe("APPROVED");
    });

    it("validateEvidenceAndProfiles succeeds when all present", async () => {
      const { wsId, depId, assessmentId } = await setupForValidation();

      const result = await validateEvidenceAndProfiles(wsId, assessmentId, depId);
      expect(result.evidenceRows.length).toBeGreaterThan(0);
      expect(result.providerProfile).toBeDefined();
      expect(result.dataProfile).toBeDefined();
    });

    it("validateCapabilityBindings allows declared capabilities", async () => {
      const { versionId } = await setupForValidation();

      const bindingIds = await validateCapabilityBindings(versionId, [
        "allowed.capability",
      ]);
      expect(bindingIds.length).toBe(1);
    });

    it("validateCapabilityBindings rejects prohibited capabilities", async () => {
      const { versionId } = await setupForValidation();

      await expect(
        validateCapabilityBindings(versionId, ["prohibited.capability"])
      ).rejects.toThrow();
    });

    it("validateCapabilityBindings rejects unknown capabilities", async () => {
      const { versionId } = await setupForValidation();

      await expect(
        validateCapabilityBindings(versionId, ["unknown.capability"])
      ).rejects.toThrow();
    });

    it("failCompliance modifies error code and throws", () => {
      const baseError = APIError.alreadyExists("Test error");

      expect(() => {
        failCompliance(baseError, "TEST_ERROR_CODE");
      }).toThrow();
    });
  });
});
