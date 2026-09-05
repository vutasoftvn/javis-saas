import { APIError } from "encore.dev/api";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { assessAiApplicability } from "./ai-legal-applicability.service";
import { getDeploymentInWorkspace, getAssessmentInWorkspace } from "./ai-compliance-access.service";
import { requireFounderCommand } from "../../shared/auth/workspace-access";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  authorizeBusinessAction,
  getLatestPolicyVersion,
} from "../../identity/services/business-authorization.service";

const {
  workspaceAiDeployments,
  aiRiskAssessments,
  aiComplianceEvidence,
  aiProviderProfiles,
  aiDataProcessingProfiles,
  aiIncidents,
  aiSystemVersions,
  aiSystemCapabilityBindings,
  legalEntityProfiles,
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
  founderMemberId?: string | bigint;
  createdByMemberId?: string | bigint;
  accountableMemberId?: string | bigint;
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
  workspaceId: string | bigint;
  deploymentId: string | bigint;
  assessmentId: string | bigint;
  approvedByMemberId: string | bigint;
  rationale: string;
  expiresAt: string;
  allowSoleProprietorshipExemption?: boolean;
}

export interface SuspendAiDeploymentInput {
  workspaceId: string | bigint;
  deploymentId: string | bigint;
  rationale: string;
  suspendedByMemberId?: string | bigint;
}

export interface ResumeAiDeploymentInput {
  workspaceId: string | bigint;
  deploymentId: string | bigint;
  rationale: string;
  resumedByMemberId: string | bigint;
}


export interface ComplianceCenterView {
  workspaceId: string;
  activeCount: number;
  incidentCount: number;
  deployments: Array<{
    id: string;
    systemVersionId: string;
    mode: string;
    status: string;
    founderMemberId: string;
    createdByMemberId?: string | null;
    accountableMemberId?: string | null;
    reviewerMemberId?: string | null;
    approvedByMemberId?: string | null;
    policyVersion?: number;
    approvedVersion?: number | null;
    technicalOwnerMemberId: string | null;
    ownerName: string;
    currentAssessmentId: string | null;
    assessmentExpiresAt: string;
    providerStatus: string;
    allowedCapabilities: string[];
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
    createdAt?: string;
  }>;
  recentIncidents: Array<{
    id: string;
    deploymentId: string;
    severity: string;
    status: string;
    summary: string;
    createdAt?: string;
  }>;
}

export async function createAiDeployment(
  input: CreateAiDeploymentInput,
  ctx?: TenantContext
): Promise<typeof workspaceAiDeployments.$inferSelect> {
  if (ctx) {
    const decision = await authorizeBusinessAction(ctx, "ai.deployment.create", {
      workspaceId: String(input.workspaceId),
    });
    if (decision.effect === "DENY") {
      const err = APIError.permissionDenied(
        `AI deployment creation denied: ${decision.reasonCodes.join(", ")}`
      );
      (err as any).code = "PERMISSION_DENIED";
      throw err;
    }
  }

  if (input.mode !== "ADVISORY_ONLY") {
    const err = APIError.invalidArgument("All AI deployments must operate in ADVISORY_ONLY mode");
    (err as any).code = "NON_ADVISORY_MODE";
    throw err;
  }

  const id = generateSnowflake();
  const callerMemberId = ctx
    ? (ctx.workforceMemberId || ctx.userId)
    : (input.createdByMemberId || generateSnowflake());
  const createdByMemberId = input.createdByMemberId || callerMemberId;
  const founderMemberId = input.founderMemberId || callerMemberId;
  const accountableMemberId = input.accountableMemberId || founderMemberId;

  const policyVersion = await getLatestPolicyVersion(BigInt(input.workspaceId));

  const [created] = await db
    .insert(workspaceAiDeployments)
    .values({
      id,
      workspaceId: BigInt(input.workspaceId),
      systemVersionId: BigInt(input.systemVersionId),
      mode: "ADVISORY_ONLY",
      status: "DRAFT",
      founderMemberId: BigInt(founderMemberId),
      createdByMemberId: BigInt(createdByMemberId),
      accountableMemberId: BigInt(accountableMemberId),
      policyVersion,
      technicalOwnerMemberId: input.technicalOwnerMemberId ? BigInt(input.technicalOwnerMemberId) : null,
    })
    .returning();

  return created;
}

export async function submitAiAssessment(
  input: SubmitAiAssessmentInput
): Promise<typeof aiRiskAssessments.$inferSelect> {
  const deployment = await getDeploymentInWorkspace(input.workspaceId, input.deploymentId);

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
      reviewerMemberId: input.reviewerMemberId ? BigInt(input.reviewerMemberId) : deployment.reviewerMemberId,
      updatedAt: new Date(),
    })
    .where(eq(workspaceAiDeployments.id, deployment.id));

  return assessment;
}

export async function approveAiAssessment(
  input: ApproveAiAssessmentInput,
  ctx?: TenantContext
): Promise<typeof workspaceAiDeployments.$inferSelect> {
  const deployment = await getDeploymentInWorkspace(input.workspaceId, input.deploymentId);
  const assessment = await getAssessmentInWorkspace(input.workspaceId, deployment.id, input.assessmentId);

  // 1. Không cho phép người tạo tự duyệt trừ phi có miễn trừ sole-proprietorship
  const creatorId = String(deployment.createdByMemberId || deployment.founderMemberId);
  const approverId = String(input.approvedByMemberId);
  if (creatorId === approverId) {
    let isSoleProprietorship = input.allowSoleProprietorshipExemption === true;
    if (!isSoleProprietorship) {
      const soleEntity = await db
        .select()
        .from(legalEntityProfiles)
        .where(
          and(
            eq(legalEntityProfiles.workspaceId, deployment.workspaceId),
            eq(legalEntityProfiles.entityType, "SOLE_PROPRIETORSHIP")
          )
        )
        .limit(1);
      isSoleProprietorship = soleEntity.length > 0;
    }

    if (!isSoleProprietorship) {
      const err = APIError.permissionDenied(
        "Creator cannot approve their own AI deployment unless sole-proprietorship exemption applies"
      );
      (err as any).code = "SELF_APPROVAL_PROHIBITED";
      throw err;
    }
  }

  // 2. Kiểm tra quyền phê duyệt qua business authorization kernel
  if (ctx) {
    const decision = await authorizeBusinessAction(
      ctx,
      "ai.deployment.approve",
      { workspaceId: String(deployment.workspaceId) },
      {
        deploymentId: String(deployment.id),
        riskClassification: assessment.classification,
      }
    );
    if (decision.effect === "DENY") {
      const err = APIError.permissionDenied(
        `AI deployment approval denied: ${decision.reasonCodes.join(", ")}`
      );
      (err as any).code = "PERMISSION_DENIED";
      throw err;
    }
  } else {
    // Không có ctx: fallback kiểm tra thẩm quyền Founder
    if (String(deployment.founderMemberId) !== String(input.approvedByMemberId)) {
      const err = APIError.permissionDenied("Founder approval required for AI deployment activation");
      (err as any).code = "FOUNDER_APPROVAL_REQUIRED";
      throw err;
    }
  }

  // 3. Precondition: Non-empty rationale
  if (!input.rationale?.trim()) {
    const err = APIError.invalidArgument("Approval requires a non-empty rationale");
    (err as any).code = "RATIONALE_REQUIRED";
    throw err;
  }

  // 4. Precondition: Expiration date in future
  const expiresDate = new Date(input.expiresAt);
  if (isNaN(expiresDate.getTime()) || expiresDate <= new Date()) {
    const err = APIError.invalidArgument("Assessment expiration date must be in the future");
    (err as any).code = "EXPIRY_IN_PAST";
    throw err;
  }

  // 5. Precondition: Statutory law check produces zero blocks
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

  // 6. Precondition: Required evidence present
  const evidence = await db
    .select()
    .from(aiComplianceEvidence)
    .where(eq(aiComplianceEvidence.assessmentId, assessment.id));

  if (evidence.length === 0) {
    const err = APIError.failedPrecondition("Compliance evidence is required before activation");
    (err as any).code = "EVIDENCE_REQUIRED";
    throw err;
  }

  // 7. Precondition: Active provider and data profile present
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
  const currentPolicyVersion = await getLatestPolicyVersion(deployment.workspaceId);
  const nextApprovedVersion = (deployment.approvedVersion || 0) + 1;

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
      approvedByMemberId: BigInt(input.approvedByMemberId),
      policyVersion: currentPolicyVersion,
      approvedVersion: nextApprovedVersion,
      updatedAt: now,
    })
    .where(eq(workspaceAiDeployments.id, deployment.id))
    .returning();

  return updatedDeployment;
}

export async function suspendAiDeployment(
  input: SuspendAiDeploymentInput
): Promise<typeof workspaceAiDeployments.$inferSelect> {
  const deployment = await getDeploymentInWorkspace(input.workspaceId, input.deploymentId);

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
  input: ResumeAiDeploymentInput,
  ctx?: TenantContext
): Promise<typeof workspaceAiDeployments.$inferSelect> {
  const deployment = await getDeploymentInWorkspace(input.workspaceId, input.deploymentId);

  if (ctx) {
    const decision = await authorizeBusinessAction(ctx, "ai.deployment.approve", {
      workspaceId: String(deployment.workspaceId),
    });
    if (decision.effect === "DENY") {
      const err = APIError.permissionDenied(
        `Resume deployment approval denied: ${decision.reasonCodes.join(", ")}`
      );
      (err as any).code = "PERMISSION_DENIED";
      throw err;
    }
  } else {
    // Resume requires authorized approver or founder
    if (
      String(deployment.founderMemberId) !== String(input.resumedByMemberId) &&
      String(deployment.approvedByMemberId) !== String(input.resumedByMemberId)
    ) {
      const err = APIError.permissionDenied("Authorized approval required to resume deployment");
      (err as any).code = "FOUNDER_APPROVAL_REQUIRED";
      throw err;
    }
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
  workspaceId: string | bigint,
  deploymentId: string | bigint
): Promise<typeof workspaceAiDeployments.$inferSelect> {
  return getDeploymentInWorkspace(workspaceId, deploymentId);
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

  const activeCount = deployments.filter((d) => d.status === "APPROVED_FOR_USE").length;
  const incidentCount = incidents.length;

  const mappedIncidents = incidents.map((i) => ({
    id: String(i.id),
    deploymentId: String(i.deploymentId),
    severity: i.severity,
    status: i.status,
    summary: i.summary,
    createdAt: i.createdAt.toISOString(),
  }));

  return {
    workspaceId: String(workspaceId),
    activeCount,
    incidentCount,
    deployments: deployments.map((d) => {
      const assess = assessments.find((a) => String(a.id) === String(d.currentAssessmentId));
      const prov = providerProfiles[0];
      return {
        id: String(d.id),
        systemVersionId: String(d.systemVersionId),
        mode: d.mode,
        status: d.status,
        founderMemberId: String(d.founderMemberId),
        createdByMemberId: d.createdByMemberId ? String(d.createdByMemberId) : null,
        accountableMemberId: d.accountableMemberId ? String(d.accountableMemberId) : null,
        reviewerMemberId: d.reviewerMemberId ? String(d.reviewerMemberId) : null,
        approvedByMemberId: d.approvedByMemberId ? String(d.approvedByMemberId) : null,
        policyVersion: d.policyVersion ?? 1,
        approvedVersion: d.approvedVersion ?? null,
        technicalOwnerMemberId: d.technicalOwnerMemberId ? String(d.technicalOwnerMemberId) : null,
        ownerName: d.technicalOwnerMemberId ? `Member ${d.technicalOwnerMemberId}` : `Founder ${d.founderMemberId}`,
        currentAssessmentId: d.currentAssessmentId ? String(d.currentAssessmentId) : null,
        assessmentExpiresAt: assess ? assess.expiresAt.toISOString() : "",
        providerStatus: prov ? prov.status : "ACTIVE",
        allowedCapabilities: [],
        createdAt: d.createdAt.toISOString(),
        updatedAt: d.updatedAt.toISOString(),
      };
    }),
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
    incidents: mappedIncidents,
    recentIncidents: mappedIncidents,
  };
}
