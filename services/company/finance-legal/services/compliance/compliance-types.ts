export interface ResolveApprovedSnapshotInput {
  workspaceId: string | bigint;
  systemKey: string;
  capabilityIds: string[];
}

export interface RuntimeComplianceSnapshot {
  workspaceId: string;
  deploymentId: string;
  assessmentId: string;
  mode: "ADVISORY_ONLY";
  status: "APPROVED_FOR_USE";
  allowedCapabilities: string[];
  capabilityBindingIds: string[];
  evidenceIds: string[];
  evidenceHashes: string[];
  legalVersionIds: string[];
  providerProfileId: string;
  providerProfileVersion: string;
  providerKey: string;
  modelKey: string;
  dataProfileId: string;
  dataProfileVersion: string;
  purposeId: string;
  retentionPolicyId: string;
  provenanceComplete: true;
  policySnapshotHash: string;
  snapshotHash: string;
  issuedAt: string;
  expiresAt: string;
}

export interface ResolveRuntimeSnapshotInput extends ResolveApprovedSnapshotInput {
  runId: string;
  policySnapshotHash: string;
}
