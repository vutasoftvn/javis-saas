import { APIError } from "encore.dev/api";
import { eq, and, desc, inArray } from "drizzle-orm";
import { db, schema } from "../../models/db";

const {
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceEvidence,
  aiProviderProfiles,
  aiDataProcessingProfiles,
  aiSystemCatalog,
  aiSystemVersions,
  aiSystemCapabilityBindings,
} = schema;

export function failCompliance(base: APIError, appCode: string): never {
  (base as any).code = appCode;
  throw base;
}

export async function validateApprovedDeployment(wsId: bigint, systemKey: string) {
  // 1) System phải tồn tại
  const [catalog] = await db
    .select()
    .from(aiSystemCatalog)
    .where(eq(aiSystemCatalog.systemKey, systemKey));

  if (!catalog) {
    throw APIError.notFound(`AI system not found for systemKey=${systemKey}`);
  }

  const versionRows = await db
    .select()
    .from(aiSystemVersions)
    .where(eq(aiSystemVersions.systemCatalogId, catalog.id));
  const versionIds = versionRows.map((v) => v.id);

  if (versionIds.length === 0) {
    throw APIError.notFound(`AI system has no versions for systemKey=${systemKey}`);
  }

  // 2) Đúng 1 deployment APPROVED_FOR_USE trong workspace cho system này
  const [deployment] = await db
    .select()
    .from(workspaceAiDeployments)
    .where(
      and(
        eq(workspaceAiDeployments.workspaceId, wsId),
        inArray(workspaceAiDeployments.systemVersionId, versionIds),
        eq(workspaceAiDeployments.status, "APPROVED_FOR_USE"),
        eq(workspaceAiDeployments.mode, "ADVISORY_ONLY")
      )
    )
    .orderBy(desc(workspaceAiDeployments.createdAt));

  if (!deployment) {
    throw APIError.notFound(
      `No approved AI deployment found for workspace=${wsId} systemKey=${systemKey}`
    );
  }

  return { catalog, deployment };
}

export async function validateApprovedAssessment(wsId: bigint, deployment: typeof workspaceAiDeployments.$inferSelect) {
  if (!deployment.currentAssessmentId) {
    failCompliance(
      APIError.alreadyExists("Deployment has no current assessment on record"),
      "ASSESSMENT_NOT_APPROVED"
    );
  }

  const [assessment] = await db
    .select()
    .from(aiRiskAssessments)
    .where(
      and(
        eq(aiRiskAssessments.id, deployment.currentAssessmentId!),
        eq(aiRiskAssessments.workspaceId, wsId)
      )
    );

  if (!assessment) {
    failCompliance(
      APIError.alreadyExists("Current assessment record could not be found"),
      "ASSESSMENT_NOT_APPROVED"
    );
  }

  if (assessment.status !== "APPROVED") {
    failCompliance(
      APIError.alreadyExists(`Current assessment status is ${assessment.status}, not APPROVED`),
      "ASSESSMENT_NOT_APPROVED"
    );
  }

  if (assessment.expiresAt.getTime() <= Date.now()) {
    failCompliance(
      APIError.alreadyExists(`Current assessment expired at ${assessment.expiresAt.toISOString()}`),
      "ASSESSMENT_EXPIRED"
    );
  }

  return assessment;
}

export async function validateEvidenceAndProfiles(
  wsId: bigint,
  assessmentId: bigint,
  deploymentId: bigint
) {
  // Evidence
  const evidenceRows = await db
    .select()
    .from(aiComplianceEvidence)
    .where(
      and(
        eq(aiComplianceEvidence.workspaceId, wsId),
        eq(aiComplianceEvidence.assessmentId, assessmentId)
      )
    )
    .orderBy(aiComplianceEvidence.id);

  if (evidenceRows.length === 0) {
    failCompliance(
      APIError.alreadyExists("Compliance evidence is required before runtime resolution"),
      "EVIDENCE_REQUIRED"
    );
  }

  // Provider profile
  const [providerProfile] = await db
    .select()
    .from(aiProviderProfiles)
    .where(
      and(eq(aiProviderProfiles.workspaceId, wsId), eq(aiProviderProfiles.status, "APPROVED"))
    )
    .orderBy(desc(aiProviderProfiles.createdAt));

  if (!providerProfile) {
    failCompliance(
      APIError.alreadyExists("An approved AI provider profile is required for runtime resolution"),
      "PROVIDER_PROFILE_REQUIRED"
    );
  }

  // Data processing profile
  const [dataProfile] = await db
    .select()
    .from(aiDataProcessingProfiles)
    .where(
      and(
        eq(aiDataProcessingProfiles.deploymentId, deploymentId),
        eq(aiDataProcessingProfiles.workspaceId, wsId),
        eq(aiDataProcessingProfiles.status, "ACTIVE")
      )
    )
    .orderBy(desc(aiDataProcessingProfiles.createdAt));

  if (!dataProfile) {
    failCompliance(
      APIError.alreadyExists("An active AI data processing profile is required for runtime resolution"),
      "DATA_PROFILE_REQUIRED"
    );
  }

  return { evidenceRows, providerProfile, dataProfile };
}

export async function validateCapabilityBindings(
  systemVersionId: bigint,
  capabilityIds: string[]
): Promise<string[]> {
  const bindingRows = await db
    .select()
    .from(aiSystemCapabilityBindings)
    .where(eq(aiSystemCapabilityBindings.systemVersionId, systemVersionId));

  const bindingByCapability = new Map(bindingRows.map((b) => [b.capabilityId, b]));
  const requestedCapabilityIds = [...capabilityIds].sort();
  const grantedBindingIds: string[] = [];

  for (const capabilityId of requestedCapabilityIds) {
    const binding = bindingByCapability.get(capabilityId);
    if (!binding || binding.prohibitedPurpose) {
      throw APIError.notFound(
        `Requested capability is out of scope for this deployment: ${capabilityId}`
      );
    }
    grantedBindingIds.push(binding.id.toString());
  }
  grantedBindingIds.sort();
  return grantedBindingIds;
}
