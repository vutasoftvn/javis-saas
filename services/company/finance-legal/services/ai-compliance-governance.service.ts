import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { assessAiApplicability } from "./ai-legal-applicability.service";

const {
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceEvidence,
  aiProviderProfiles,
  aiDataProcessingProfiles,
  aiIncidents,
  aiSystemVersions,
} = schema;

export type DeploymentStatus =
  | "DRAFT"
  | "ASSESSED"
  | "APPROVED_FOR_USE"
  | "SUSPENDED"
  | "REJECTED"
  | "RETIRED";

const transitions: Record<DeploymentStatus, readonly DeploymentStatus[]> = {
  DRAFT: ["ASSESSED", "REJECTED"],
  ASSESSED: ["APPROVED_FOR_USE", "REJECTED", "SUSPENDED"],
  APPROVED_FOR_USE: ["SUSPENDED", "RETIRED"],
  SUSPENDED: ["APPROVED_FOR_USE", "RETIRED"],
  REJECTED: [],
  RETIRED: [],
};

export function assertTransition(from: DeploymentStatus, to: DeploymentStatus): void {
  if (!transitions[from]?.includes(to)) {
    const err = APIError.invalidArgument(`Invalid AI deployment transition from ${from} to ${to}`);
    (err as any).code = "INVALID_DEPLOYMENT_TRANSITION";
    throw err;
  }
}

export interface CreateAiDeploymentInput {
  workspaceId: string | bigint;
  systemVersionId: string | bigint;
  mode: "ADVISORY_ONLY";
  founderMemberId: string | bigint;
  technicalOwnerMemberId?: string | bigint;
}

export interface SubmitAiAssessmentInput {
  workspaceId: string | bigint;
  deploymentId: string | bigint;
  classification: "OUT_OF_CATALOG" | "REQUIRES_REVIEW" | "HIGH_RISK";
  intendedPurpose: string;
  controls: string[];
  affectedStakeholders?: string[];
  reviewerMemberId?: string | bigint;
  expiresAt: string;
}

export interface ApproveAiAssessmentInput {
  deploymentId: string | bigint;
  assessmentId: string | bigint;
  approvedByMemberId: string | bigint;
  rationale: string;
  expiresAt: string;
}

export interface SuspendAiDeploymentInput {
  deploymentId: string | bigint;
  rationale: string;
  suspendedByMemberId?: string | bigint;
}

export interface ResumeAiDeploymentInput {
  deploymentId: string | bigint;
  rationale: string;
  resumedByMemberId: string | bigint;
}


export interface ComplianceCenterView {
  workspaceId: string;
  deployments: Array<{
    id: string;
    systemVersionId: string;
    mode: string;
    status: string;
    founderMemberId: string;
    technicalOwnerMemberId: string | null;
    currentAssessmentId: string | null;
    createdAt: string;
    updatedAt: string;
  }>;
  assessments: Array<{
    id: string;
    deploymentId: string;
    classification: string;
    status: string;
    expiresAt: string;
  }>;
  providerProfiles: Array<{
    id: string;
    providerKey: string;
    modelKey: string;
    version: string;
    status: string;
  }>;
  incidents: Array<{
    id: string;
    deploymentId: string;
    severity: string;
    status: string;
    summary: string;
  }>;
}

export async function createAiDeployment(
  input: CreateAiDeploymentInput
): Promise<typeof workspaceAiDeployments.$inferSelect> {
  if (input.mode !== "ADVISORY_ONLY") {
    const err = APIError.invalidArgument("All AI deployments must operate in ADVISORY_ONLY mode");
    (err as any).code = "NON_ADVISORY_MODE";
    throw err;
  }

  const id = generateSnowflake();
  const [created] = await db
    .insert(workspaceAiDeployments)
    .values({
      id,
      workspaceId: BigInt(input.workspaceId),
      systemVersionId: BigInt(input.systemVersionId),
      mode: "ADVISORY_ONLY",
      status: "DRAFT",
      founderMemberId: BigInt(input.founderMemberId),
      technicalOwnerMemberId: input.technicalOwnerMemberId ? BigInt(input.technicalOwnerMemberId) : null,
    })
    .returning();

  return created;
}

export async function submitAiAssessment(
  input: SubmitAiAssessmentInput
): Promise<typeof aiRiskAssessments.$inferSelect> {
  const [deployment] = await db
    .select()
    .from(workspaceAiDeployments)
    .where(eq(workspaceAiDeployments.id, BigInt(input.deploymentId)));

  if (!deployment) {
    throw APIError.notFound("AI deployment not found");
  }

  assertTransition(deployment.status as DeploymentStatus, "ASSESSED");

  const assessmentId = generateSnowflake();
  const [assessment] = await db
    .insert(aiRiskAssessments)
    .values({
      id: assessmentId,
      workspaceId: deployment.workspaceId,
      deploymentId: deployment.id,
      classification: input.classification,
      intendedPurpose: input.intendedPurpose,
      affectedStakeholders: input.affectedStakeholders || [],
      controls: input.controls || [],
      reviewerMemberId: input.reviewerMemberId ? BigInt(input.reviewerMemberId) : null,
      expiresAt: new Date(input.expiresAt),
      status: "PENDING",
    })
    .returning();

  await db
    .update(workspaceAiDeployments)
    .set({
      status: "ASSESSED",
      currentAssessmentId: assessment.id,
      updatedAt: new Date(),
    })
    .where(eq(workspaceAiDeployments.id, deployment.id));

  return assessment;
}

export async function approveAiAssessment(
  input: ApproveAiAssessmentInput
): Promise<typeof workspaceAiDeployments.$inferSelect> {
  const [deployment] = await db
    .select()
    .from(workspaceAiDeployments)
    .where(eq(workspaceAiDeployments.id, BigInt(input.deploymentId)));

  if (!deployment) {
    throw APIError.notFound("AI deployment not found");
  }

  const [assessment] = await db
    .select()
    .from(aiRiskAssessments)
    .where(
      and(
        eq(aiRiskAssessments.id, BigInt(input.assessmentId)),
        eq(aiRiskAssessments.deploymentId, deployment.id)
      )
    );

  if (!assessment) {
    throw APIError.notFound("Assessment not found for this deployment");
  }

  // Precondition: Founder approval required
  if (String(deployment.founderMemberId) !== String(input.approvedByMemberId)) {
    const err = APIError.permissionDenied("Founder approval required for AI deployment activation");
    (err as any).code = "FOUNDER_APPROVAL_REQUIRED";
    throw err;
  }

  // Precondition: Non-empty rationale
  if (!input.rationale?.trim()) {
    const err = APIError.invalidArgument("Approval requires a non-empty rationale");
    (err as any).code = "RATIONALE_REQUIRED";
    throw err;
  }

  // Precondition: Expiration date in future
  const expiresDate = new Date(input.expiresAt);
  if (isNaN(expiresDate.getTime()) || expiresDate <= new Date()) {
    const err = APIError.invalidArgument("Assessment expiration date must be in the future");
    (err as any).code = "EXPIRY_IN_PAST";
    throw err;
  }

  // Precondition: Statutory law check produces zero blocks
  const statutoryCheck = await assessAiApplicability({
    workspaceId: String(deployment.workspaceId),
    deploymentMode: deployment.mode,
    intendedPurpose: assessment.intendedPurpose,
    decisionDomain: "GENERAL",
    capabilityEffectClass: "DRAFT",
    dataCategories: ["BUSINESS_CONFIDENTIAL"],
    providerProfileStatus: "APPROVED",
    lastAssessmentAt: new Date().toISOString(),
  });

  if (statutoryCheck.currentLawBlocks.length > 0) {
    const err = APIError.failedPrecondition(
      `Statutory controls block deployment activation: ${statutoryCheck.currentLawBlocks.join(", ")}`
    );
    (err as any).code = "STATUTORY_BLOCK";
    throw err;
  }

  // Precondition: Required evidence present
  const evidence = await db
    .select()
    .from(aiComplianceEvidence)
    .where(eq(aiComplianceEvidence.assessmentId, assessment.id));

  if (evidence.length === 0) {
    const err = APIError.failedPrecondition("Compliance evidence is required before activation");
    (err as any).code = "EVIDENCE_REQUIRED";
    throw err;
  }

  // Precondition: Active provider and data profile present
  const providerProfiles = await db
    .select()
    .from(aiProviderProfiles)
    .where(
      and(
        eq(aiProviderProfiles.workspaceId, deployment.workspaceId),
        eq(aiProviderProfiles.status, "APPROVED")
      )
    );

  const dataProfiles = await db
    .select()
    .from(aiDataProcessingProfiles)
    .where(
      and(
        eq(aiDataProcessingProfiles.deploymentId, deployment.id),
        eq(aiDataProcessingProfiles.status, "ACTIVE")
      )
    );

  if (providerProfiles.length === 0 || dataProfiles.length === 0) {
    const err = APIError.failedPrecondition("Active provider and data processing profiles are required");
    (err as any).code = "PROFILES_REQUIRED";
    throw err;
  }

  assertTransition(deployment.status as DeploymentStatus, "APPROVED_FOR_USE");

  const now = new Date();
  await db
    .update(aiRiskAssessments)
    .set({
      status: "APPROVED",
      approvedByMemberId: BigInt(input.approvedByMemberId),
      approvedAt: now,
      rationale: input.rationale,
      expiresAt: expiresDate,
      updatedAt: now,
    })
    .where(eq(aiRiskAssessments.id, assessment.id));

  const [updatedDeployment] = await db
    .update(workspaceAiDeployments)
    .set({
      status: "APPROVED_FOR_USE",
      currentAssessmentId: assessment.id,
      updatedAt: now,
    })
    .where(eq(workspaceAiDeployments.id, deployment.id))
    .returning();

  return updatedDeployment;
}

export async function suspendAiDeployment(
  input: SuspendAiDeploymentInput
): Promise<typeof workspaceAiDeployments.$inferSelect> {
  const [deployment] = await db
    .select()
    .from(workspaceAiDeployments)
    .where(eq(workspaceAiDeployments.id, BigInt(input.deploymentId)));

  if (!deployment) {
    throw APIError.notFound("AI deployment not found");
  }

  if (deployment.status === "SUSPENDED") {
    return deployment;
  }

  assertTransition(deployment.status as DeploymentStatus, "SUSPENDED");


  const [updated] = await db
    .update(workspaceAiDeployments)
    .set({
      status: "SUSPENDED",
      updatedAt: new Date(),
    })
    .where(eq(workspaceAiDeployments.id, deployment.id))
    .returning();

  return updated;
}

export async function resumeAiDeployment(
  input: ResumeAiDeploymentInput
): Promise<typeof workspaceAiDeployments.$inferSelect> {
  const [deployment] = await db
    .select()
    .from(workspaceAiDeployments)
    .where(eq(workspaceAiDeployments.id, BigInt(input.deploymentId)));

  if (!deployment) {
    throw APIError.notFound("AI deployment not found");
  }

  // Resume requires Founder approval
  if (String(deployment.founderMemberId) !== String(input.resumedByMemberId)) {
    const err = APIError.permissionDenied("Founder approval required to resume deployment");
    (err as any).code = "FOUNDER_APPROVAL_REQUIRED";
    throw err;
  }

  // Check no open CRITICAL incident exists for this deployment
  const openCriticalIncidents = await db
    .select()
    .from(aiIncidents)
    .where(
      and(
        eq(aiIncidents.deploymentId, deployment.id),
        eq(aiIncidents.severity, "CRITICAL"),
        eq(aiIncidents.status, "OPEN")
      )
    );

  if (openCriticalIncidents.length > 0) {
    const err = APIError.failedPrecondition("Cannot resume deployment while a CRITICAL incident is OPEN");
    (err as any).code = "CRITICAL_INCIDENT_OPEN";
    throw err;
  }

  assertTransition(deployment.status as DeploymentStatus, "APPROVED_FOR_USE");

  const [updated] = await db
    .update(workspaceAiDeployments)
    .set({
      status: "APPROVED_FOR_USE",
      updatedAt: new Date(),
    })
    .where(eq(workspaceAiDeployments.id, deployment.id))
    .returning();

  return updated;
}

export async function getDeployment(
  deploymentId: string | bigint
): Promise<typeof workspaceAiDeployments.$inferSelect> {
  const [deployment] = await db
    .select()
    .from(workspaceAiDeployments)
    .where(eq(workspaceAiDeployments.id, BigInt(deploymentId)));

  if (!deployment) {
    throw APIError.notFound("AI deployment not found");
  }

  return deployment;
}

export async function getComplianceCenterView(
  workspaceId: string | bigint
): Promise<ComplianceCenterView> {
  const wsId = BigInt(workspaceId);

  const deployments = await db
    .select()
    .from(workspaceAiDeployments)
    .where(eq(workspaceAiDeployments.workspaceId, wsId));

  const assessments = await db
    .select()
    .from(aiRiskAssessments)
    .where(eq(aiRiskAssessments.workspaceId, wsId));

  const providerProfiles = await db
    .select()
    .from(aiProviderProfiles)
    .where(eq(aiProviderProfiles.workspaceId, wsId));

  const incidents = await db
    .select()
    .from(aiIncidents)
    .where(eq(aiIncidents.workspaceId, wsId));

  return {
    workspaceId: String(workspaceId),
    deployments: deployments.map((d) => ({
      id: String(d.id),
      systemVersionId: String(d.systemVersionId),
      mode: d.mode,
      status: d.status,
      founderMemberId: String(d.founderMemberId),
      technicalOwnerMemberId: d.technicalOwnerMemberId ? String(d.technicalOwnerMemberId) : null,
      currentAssessmentId: d.currentAssessmentId ? String(d.currentAssessmentId) : null,
      createdAt: d.createdAt.toISOString(),
      updatedAt: d.updatedAt.toISOString(),
    })),
    assessments: assessments.map((a) => ({
      id: String(a.id),
      deploymentId: String(a.deploymentId),
      classification: a.classification,
      status: a.status,
      expiresAt: a.expiresAt.toISOString(),
    })),
    providerProfiles: providerProfiles.map((p) => ({
      id: String(p.id),
      providerKey: p.providerKey,
      modelKey: p.modelKey,
      version: p.version,
      status: p.status,
    })),
    incidents: incidents.map((i) => ({
      id: String(i.id),
      deploymentId: String(i.deploymentId),
      severity: i.severity,
      status: i.status,
      summary: i.summary,
    })),
  };
}
