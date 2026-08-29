import { describe, expect, it } from "vitest";
import {
  reportAiIncident,
  resolveAiIncident,
  evaluateCircuitBreakers,
  type ReportAiIncidentInput,
} from "../services/ai-incident-response.service";
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

describe("AI incident response and circuit breakers", () => {
  async function setupActiveDeployment() {
    const wsId = String(generateSnowflake());
    const founderId = String(generateSnowflake());
    const catalogId = generateSnowflake();
    const versionId = generateSnowflake();

    await db.insert(aiSystemCatalog).values({
      id: catalogId,
      systemKey: `system-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: "Agent System",
      allowedPurposes: ["advisory"],
      prohibitedPurposes: [],
      lifecycleStatus: "ACTIVE",
    });

    await db.insert(aiSystemVersions).values({
      id: versionId,
      systemCatalogId: catalogId,
      version: "1.0.0",
      configHash: "sha256:cfg",
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
      deploymentId: String(deployment.id),
      assessmentId: String(assessment.id),
      approvedByMemberId: founderId,
      rationale: "Approved",
      expiresAt: "2027-01-01T00:00:00Z",
    });

    return { wsId, founderId, deploymentId: String(deployment.id) };
  }

  it("trips circuit breaker and suspends deployment on three critical incidents", async () => {
    const { wsId, founderId, deploymentId } = await setupActiveDeployment();

    const makeIncidentInput = (num: number): ReportAiIncidentInput => ({
      workspaceId: wsId,
      deploymentId,
      severity: "CRITICAL",
      incidentType: "STATUTORY_VIOLATION",
      summary: `Critical incident #${num}`,
      reportedByMemberId: founderId,
    });

    const inc1 = await reportAiIncident(makeIncidentInput(1));
    expect(inc1.breakerTripped).toBe(false);

    const inc2 = await reportAiIncident(makeIncidentInput(2));
    expect(inc2.breakerTripped).toBe(false);

    const inc3 = await reportAiIncident(makeIncidentInput(3));
    expect(inc3.breakerTripped).toBe(true);

    const deployment = await getDeployment(deploymentId);
    expect(deployment.status).toBe("SUSPENDED");
  });

  it("resolves an incident and records action", async () => {
    const { wsId, founderId, deploymentId } = await setupActiveDeployment();

    const incident = await reportAiIncident({
      workspaceId: wsId,
      deploymentId,
      severity: "LOW",
      incidentType: "DATA_MINIMIZATION_GAP",
      summary: "Minor logging gap",
      reportedByMemberId: founderId,
    });

    const resolved = await resolveAiIncident({
      incidentId: String(incident.id),
      resolvedByMemberId: founderId,
      actionTaken: "Updated log filter to sanitize keys",
    });

    expect(resolved.status).toBe("CLOSED");
  });
});

