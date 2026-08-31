import { APIError } from "encore.dev/api";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { getComplianceSnapshotInWorkspace } from "./ai-compliance-access.service";
import { assessAiApplicability } from "./ai-legal-applicability.service";
import {
  canonicalJsonStringify,
  computeCanonicalSha256,
} from "./compliance/canonical-hasher";
import {
  ResolveApprovedSnapshotInput,
  RuntimeComplianceSnapshot,
  ResolveRuntimeSnapshotInput,
} from "./compliance/compliance-types";
import {
  failCompliance,
  validateApprovedDeployment,
  validateApprovedAssessment,
  validateEvidenceAndProfiles,
  validateCapabilityBindings,
} from "./compliance/compliance-precondition-validator";
import * as repo from "./compliance/compliance-snapshot.repository";

// Re-exports to guarantee 100% backward compatibility
export {
  canonicalJsonStringify,
  computeCanonicalSha256,
  ResolveApprovedSnapshotInput,
  RuntimeComplianceSnapshot,
  ResolveRuntimeSnapshotInput,
};

export async function resolveApprovedComplianceSnapshot(
  input: ResolveApprovedSnapshotInput
): Promise<RuntimeComplianceSnapshot> {
  const wsId = BigInt(input.workspaceId);

  if (!input.capabilityIds || input.capabilityIds.length === 0) {
    throw APIError.invalidArgument(
      "capabilityIds must be a non-empty list — runtime resolution cannot grant an unscoped snapshot"
    );
  }

  // 1 & 2) Validate Catalog & Deployment
  const { catalog, deployment } = await validateApprovedDeployment(wsId, input.systemKey);

  // 3) Validate Assessment
  const assessment = await validateApprovedAssessment(wsId, deployment);

  // 4, 5, 6) Validate Evidence, Provider Profile, Data Profile
  const { evidenceRows, providerProfile, dataProfile } = await validateEvidenceAndProfiles(
    wsId,
    assessment.id,
    deployment.id
  );

  // 7) Validate Capability Bindings
  const requestedCapabilityIds = [...input.capabilityIds].sort();
  const grantedBindingIds = await validateCapabilityBindings(
    deployment.systemVersionId,
    requestedCapabilityIds
  );

  const providerProfileId = providerProfile.id;
  const dataProfileId = dataProfile.id;
  const modelKey = providerProfile.modelKey;

  const evidencePairs = evidenceRows
    .map((e) => ({ id: e.id.toString(), contentHash: e.contentHash }))
    .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  const evidenceIds = evidencePairs.map((e) => e.id);
  const evidenceHashes = evidencePairs.map((e) => e.contentHash);

  // 8) Legal provenance & applicability
  const evalDate = new Date();
  const applicabilityResult = await assessAiApplicability({
    workspaceId: wsId.toString(),
    deploymentMode: deployment.mode,
    intendedPurpose: assessment.intendedPurpose,
    decisionDomain: (catalog as any).decisionDomain ?? "GENERAL",
    providerProfileStatus: providerProfile.status,
    lastAssessmentAt: assessment.approvedAt ? assessment.approvedAt.toISOString() : assessment.createdAt.toISOString(),
    asOfDate: evalDate,
  });

  if (applicabilityResult.blockingRule || applicabilityResult.currentLawBlocks.length > 0) {
    failCompliance(
      APIError.alreadyExists(
        `Deployment blocked by legal rule ${applicabilityResult.blockingRule?.ruleId ?? applicabilityResult.currentLawBlocks[0]}`
      ),
      "LEGAL_RULE_BLOCKED"
    );
  }

  if (applicabilityResult.professionalReviewRequired.length > 0) {
    failCompliance(
      APIError.alreadyExists(
        `Deployment requires human legal review before runtime approval: ${applicabilityResult.professionalReviewRequired.join(", ")}`
      ),
      "LEGAL_REVIEW_PENDING"
    );
  }

  for (const rule of applicabilityResult.matchedRules) {
    if (rule.mandatoryEvidenceType) {
      const hasEvidence = evidenceRows.some(
        (e) => e.evidenceType === rule.mandatoryEvidenceType && (e as any).conclusion !== "NON_COMPLIANT"
      );
      if (!hasEvidence) {
        failCompliance(
          APIError.alreadyExists(
            `Mandatory compliance evidence missing for rule ${rule.ruleId}: ${rule.mandatoryEvidenceType}`
          ),
          "MANDATORY_EVIDENCE_MISSING"
        );
      }
    }
  }

  const legalVersionMap = new Map<string, string>();
  for (const rule of applicabilityResult.matchedRules) {
    if (rule.sourceVersionId && rule.sourceContentHash) {
      legalVersionMap.set(rule.sourceVersionId, rule.sourceContentHash);
    }
  }

  const legalVersionPairs = Array.from(legalVersionMap.entries())
    .map(([id, contentHash]) => ({ id, contentHash }))
    .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  const legalVersionIds = legalVersionPairs.map((p) => p.id);

  const providerProfileVersion = providerProfile.version;
  const dataProfileVersion = dataProfile.version;

  const policySnapshotHash = computeCanonicalSha256({
    workspaceId: wsId.toString(),
    deploymentId: deployment.id.toString(),
    assessmentId: assessment.id.toString(),
    mode: "ADVISORY_ONLY",
    status: "APPROVED_FOR_USE",
    allowedCapabilities: requestedCapabilityIds,
    providerProfileVersion,
    dataProfileVersion,
  });

  const issuedAt = new Date();
  let expiryTimestamp = assessment.expiresAt.getTime();
  for (const rule of applicabilityResult.matchedRules) {
    if (rule.effectiveTo) {
      const toTime = new Date(rule.effectiveTo).getTime();
      if (!isNaN(toTime) && toTime < expiryTimestamp) {
        expiryTimestamp = toTime;
      }
    }
  }
  const expiresAt = new Date(expiryTimestamp);

  const canonicalPayload = {
    workspaceId: wsId.toString(),
    deploymentId: deployment.id.toString(),
    assessmentId: assessment.id.toString(),
    assessmentExpiresAt: assessment.expiresAt.toISOString(),
    capabilityBindingIds: grantedBindingIds,
    evidence: evidencePairs,
    legalVersions: legalVersionPairs,
    providerProfileId: providerProfileId.toString(),
    providerProfileVersion,
    modelKey,
    dataProfileId: dataProfileId.toString(),
    dataProfileVersion,
    policySnapshotHash,
    issuedAt: issuedAt.toISOString(),
    expiresAt: expiresAt.toISOString(),
  };

  const snapshotHash = computeCanonicalSha256(canonicalPayload);

  return {
    workspaceId: wsId.toString(),
    deploymentId: deployment.id.toString(),
    assessmentId: assessment.id.toString(),
    mode: "ADVISORY_ONLY",
    status: "APPROVED_FOR_USE",
    allowedCapabilities: requestedCapabilityIds,
    capabilityBindingIds: grantedBindingIds,
    evidenceIds,
    evidenceHashes,
    legalVersionIds,
    providerProfileId: providerProfileId.toString(),
    providerProfileVersion,
    providerKey: providerProfile.providerKey,
    modelKey: providerProfile.modelKey,
    dataProfileId: dataProfileId.toString(),
    dataProfileVersion,
    purposeId: dataProfile.purposeId,
    retentionPolicyId: dataProfile.retentionPolicyId,
    provenanceComplete: true,
    policySnapshotHash,
    snapshotHash,
    issuedAt: issuedAt.toISOString(),
    expiresAt: expiresAt.toISOString(),
  };
}

export async function resolveRuntimeComplianceSnapshot(
  input: ResolveRuntimeSnapshotInput
): Promise<RuntimeComplianceSnapshot> {
  return resolveApprovedComplianceSnapshot(input);
}

export async function captureComplianceSnapshot(
  workspaceId: string | bigint,
  deploymentIdInput?: string | bigint
) {
  const wsId = BigInt(workspaceId);
  const deployment = await repo.findDeploymentForCapture(wsId, deploymentIdInput);

  if (!deployment) {
    throw APIError.notFound(
      `No AI deployment found for workspace=${workspaceId} — capture requires an existing deployment, it never creates one`
    );
  }

  const systemKey = await repo.getSystemKeyForVersion(deployment.systemVersionId);
  const capabilityIds = await repo.getDeclaredCapabilityIds(deployment.systemVersionId);

  const resolved = await resolveApprovedComplianceSnapshot({
    workspaceId: wsId,
    systemKey,
    capabilityIds,
  });

  const snapshotId = generateSnowflake();

  return repo.insertComplianceSnapshotRecord({
    id: snapshotId,
    workspaceId: wsId,
    deploymentId: BigInt(resolved.deploymentId),
    assessmentId: BigInt(resolved.assessmentId),
    mode: resolved.mode,
    status: resolved.status,
    allowedCapabilities: resolved.allowedCapabilities,
    providerProfileVersion: resolved.providerProfileVersion,
    dataProfileVersion: resolved.dataProfileVersion,
    legalVersionIds: resolved.legalVersionIds,
    capabilityBindingIds: resolved.capabilityBindingIds,
    evidenceIds: resolved.evidenceIds,
    evidenceHashes: resolved.evidenceHashes,
    providerProfileId: BigInt(resolved.providerProfileId),
    dataProfileId: BigInt(resolved.dataProfileId),
    provenanceComplete: resolved.provenanceComplete,
    policySnapshotHash: resolved.policySnapshotHash,
    snapshotHash: resolved.snapshotHash,
    issuedAt: new Date(resolved.issuedAt),
    expiresAt: new Date(resolved.expiresAt),
  });
}

export async function verifySnapshotIntegrity(
  workspaceId: string | bigint,
  snapshotId: string | bigint
): Promise<boolean> {
  const snapshot = await getComplianceSnapshotInWorkspace(workspaceId, snapshotId);

  let modelKey: string | null = null;
  if (snapshot.providerProfileId) {
    const providerProfile = await repo.findProviderProfileById(snapshot.providerProfileId);
    modelKey = providerProfile?.modelKey ?? null;
  }

  const evidenceIds = (snapshot.evidenceIds as string[]) || [];
  const evidenceHashes = (snapshot.evidenceHashes as string[]) || [];
  const evidencePairs = evidenceIds.map((id, i) => ({ id, contentHash: evidenceHashes[i] }));

  const legalVersionIds = (snapshot.legalVersionIds as string[]) || [];
  let legalVersionPairs: Array<{ id: string; contentHash: string }> = [];
  if (legalVersionIds.length > 0) {
    const versionRows = await repo.findRegulationVersionsByIds(legalVersionIds);
    const versionMap = new Map(versionRows.map((v) => [String(v.id), v.contentHash || ""]));
    legalVersionPairs = legalVersionIds
      .map((id) => ({ id, contentHash: versionMap.get(id) || "" }))
      .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  }

  const assessment = await repo.findRiskAssessmentById(snapshot.assessmentId);
  const assessmentExpiresAt = assessment?.expiresAt ? assessment.expiresAt.toISOString() : snapshot.expiresAt.toISOString();

  const canonicalPayload = {
    workspaceId: snapshot.workspaceId.toString(),
    deploymentId: snapshot.deploymentId.toString(),
    assessmentId: snapshot.assessmentId.toString(),
    assessmentExpiresAt,
    capabilityBindingIds: (snapshot.capabilityBindingIds as string[]) || [],
    evidence: evidencePairs,
    legalVersions: legalVersionPairs,
    providerProfileId: snapshot.providerProfileId ? snapshot.providerProfileId.toString() : null,
    providerProfileVersion: snapshot.providerProfileVersion,
    modelKey,
    dataProfileId: snapshot.dataProfileId ? snapshot.dataProfileId.toString() : null,
    dataProfileVersion: snapshot.dataProfileVersion,
    policySnapshotHash: snapshot.policySnapshotHash,
    issuedAt: snapshot.issuedAt.toISOString(),
    expiresAt: snapshot.expiresAt.toISOString(),
  };

  const calculatedHash = computeCanonicalSha256(canonicalPayload);
  return calculatedHash === snapshot.snapshotHash;
}

export async function listSnapshots(workspaceId: string | bigint) {
  return repo.listComplianceSnapshots(BigInt(workspaceId));
}
