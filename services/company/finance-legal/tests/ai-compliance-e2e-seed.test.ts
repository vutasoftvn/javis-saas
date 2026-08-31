import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { seedE2eComplianceScenario } from "../services/ai-compliance-e2e-seed.service";
import { db, schema } from "../models/db";

const {
  aiSystemCatalog,
  aiSystemVersions,
  aiSystemCapabilityBindings,
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceEvidence,
  aiProviderProfiles,
  aiDataProcessingProfiles,
  dataProcessingAuthorizations,
} = schema;

describe("AI Compliance E2E Seed", () => {
  it("seeds an 'approved' scenario with all required records", async () => {
    const result = await seedE2eComplianceScenario("approved");

    // Verify result contains all expected fields
    expect(result.workspaceId).toBeDefined();
    expect(result.founderId).toBeDefined();
    expect(result.systemKey).toBeDefined();
    expect(result.deploymentId).toBeDefined();
    expect(result.assessmentId).toBeDefined();
    expect(result.providerProfileId).toBeDefined();
    expect(result.dataProfileId).toBeDefined();
    expect(result.subjectReference).toBeUndefined();
    expect(result.authorizationId).toBeUndefined();

    // Verify deployment exists and is APPROVED_FOR_USE
    const [deployment] = await db
      .select()
      .from(workspaceAiDeployments)
      .where(eq(workspaceAiDeployments.id, BigInt(result.deploymentId)));

    expect(deployment).toBeDefined();
    expect(deployment.status).toBe("APPROVED_FOR_USE");
    expect(deployment.mode).toBe("ADVISORY_ONLY");

    // Verify assessment exists and is APPROVED
    const [assessment] = await db
      .select()
      .from(aiRiskAssessments)
      .where(eq(aiRiskAssessments.id, BigInt(result.assessmentId)));

    expect(assessment).toBeDefined();
    expect(assessment.status).toBe("APPROVED");
    expect(assessment.expiresAt.getTime()).toBeGreaterThan(Date.now());

    // Verify evidence exists
    const evidence = await db
      .select()
      .from(aiComplianceEvidence)
      .where(eq(aiComplianceEvidence.assessmentId, BigInt(result.assessmentId)));

    expect(evidence.length).toBeGreaterThan(0);

    // Verify provider profile exists and is APPROVED
    const [provider] = await db
      .select()
      .from(aiProviderProfiles)
      .where(eq(aiProviderProfiles.id, BigInt(result.providerProfileId)));

    expect(provider).toBeDefined();
    expect(provider.status).toBe("APPROVED");

    // Verify data profile exists and is ACTIVE
    const [dataProfile] = await db
      .select()
      .from(aiDataProcessingProfiles)
      .where(eq(aiDataProcessingProfiles.id, BigInt(result.dataProfileId)));

    expect(dataProfile).toBeDefined();
    expect(dataProfile.status).toBe("ACTIVE");
  });

  it("seeds a 'suspended' scenario with SUSPENDED deployment", async () => {
    const result = await seedE2eComplianceScenario("suspended");

    const [deployment] = await db
      .select()
      .from(workspaceAiDeployments)
      .where(eq(workspaceAiDeployments.id, BigInt(result.deploymentId)));

    expect(deployment.status).toBe("SUSPENDED");
  });

  it("seeds an 'expired_assessment' scenario with assessment in the past", async () => {
    const result = await seedE2eComplianceScenario("expired_assessment");

    const [assessment] = await db
      .select()
      .from(aiRiskAssessments)
      .where(eq(aiRiskAssessments.id, BigInt(result.assessmentId)));

    expect(assessment.status).toBe("APPROVED");
    expect(assessment.expiresAt.getTime()).toBeLessThan(Date.now());
  });

  it("seeds a 'revoked_authorization' scenario with withdrawn authorization", async () => {
    const result = await seedE2eComplianceScenario("revoked_authorization");

    expect(result.subjectReference).toBeDefined();
    expect(result.authorizationId).toBeDefined();

    const [authorization] = await db
      .select()
      .from(dataProcessingAuthorizations)
      .where(eq(dataProcessingAuthorizations.id, BigInt(result.authorizationId!)));

    expect(authorization).toBeDefined();
    expect(authorization.status).toBe("WITHDRAWN");
  });

  it("is idempotent with fixed systemKey — calling twice does not fail", async () => {
    const systemKey = `e2e-idempotent-test-${Date.now()}`;

    const result1 = await seedE2eComplianceScenario("approved", { systemKey });
    const result2 = await seedE2eComplianceScenario("approved", { systemKey });

    // Both should have the same systemKey
    expect(result1.systemKey).toBe(systemKey);
    expect(result2.systemKey).toBe(systemKey);

    // Verify that system catalog is reused (not duplicated)
    const catalogs = await db
      .select()
      .from(aiSystemCatalog)
      .where(eq(aiSystemCatalog.systemKey, systemKey));

    expect(catalogs.length).toBe(1);
  });

  it("binds additional capabilities when provided", async () => {
    const systemKey = `e2e-capability-test-${Date.now()}`;
    const additionalCapabilities = ["operations.task.read", "operations.task.write"];

    const result = await seedE2eComplianceScenario("approved", {
      systemKey,
      additionalBoundCapabilityIds: additionalCapabilities,
    });

    const [deployment] = await db
      .select()
      .from(workspaceAiDeployments)
      .where(eq(workspaceAiDeployments.id, BigInt(result.deploymentId)));

    // Get the system version
    const [version] = await db
      .select()
      .from(aiSystemVersions)
      .where(eq(aiSystemVersions.id, deployment.systemVersionId));

    // Get all bindings for this version
    const bindings = await db
      .select()
      .from(aiSystemCapabilityBindings)
      .where(eq(aiSystemCapabilityBindings.systemVersionId, version.id));

    const boundCapabilities = bindings.map((b) => b.capabilityId);

    // Should have base capabilities + additional
    expect(boundCapabilities).toContain("operations.task.list");
    expect(boundCapabilities).toContain("model.input.direct-user-message");
    for (const cap of additionalCapabilities) {
      expect(boundCapabilities).toContain(cap);
    }
  });

  it("handles multiple scenarios in same test run without interference", async () => {
    const approved = await seedE2eComplianceScenario("approved");
    const suspended = await seedE2eComplianceScenario("suspended");
    const expired = await seedE2eComplianceScenario("expired_assessment");

    // Verify they are different workspaces
    expect(approved.workspaceId).not.toBe(suspended.workspaceId);
    expect(suspended.workspaceId).not.toBe(expired.workspaceId);

    // Verify each has correct status
    const [approvedDeployment] = await db
      .select()
      .from(workspaceAiDeployments)
      .where(eq(workspaceAiDeployments.id, BigInt(approved.deploymentId)));
    expect(approvedDeployment.status).toBe("APPROVED_FOR_USE");

    const [suspendedDeployment] = await db
      .select()
      .from(workspaceAiDeployments)
      .where(eq(workspaceAiDeployments.id, BigInt(suspended.deploymentId)));
    expect(suspendedDeployment.status).toBe("SUSPENDED");

    const [expiredAssessment] = await db
      .select()
      .from(aiRiskAssessments)
      .where(eq(aiRiskAssessments.id, BigInt(expired.assessmentId)));
    expect(expiredAssessment.expiresAt.getTime()).toBeLessThan(Date.now());
  });
});
