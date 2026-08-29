import { api, Header } from "encore.dev/api";
import { APIError } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  createAiDeployment,
  submitAiAssessment,
  approveAiAssessment,
  suspendAiDeployment,
  resumeAiDeployment,
  getComplianceCenterView,
  ComplianceCenterView,
} from "../services/ai-compliance-governance.service";

export interface CreateAiDeploymentRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  systemVersionId: string;
  technicalOwnerMemberId?: string;
}

export interface SubmitAiAssessmentRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  deploymentId: string;
  classification: "OUT_OF_CATALOG" | "REQUIRES_REVIEW" | "HIGH_RISK";
  intendedPurpose: string;
  controls: string[];
  affectedStakeholders?: string[];
  expiresAt: string;
}

export interface ApproveAiAssessmentRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  deploymentId: string;
  assessmentId: string;
  rationale: string;
  expiresAt: string;
}

export interface SuspendAiDeploymentRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  deploymentId: string;
  rationale: string;
}

export interface ResumeAiDeploymentRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  deploymentId: string;
  rationale: string;
}

export interface GetComplianceCenterViewRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export const createAiDeploymentApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/deployments", expose: true },
  async (req: CreateAiDeploymentRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    const memberId = ctx.workforceMemberId || ctx.userId;
    return createAiDeployment({
      workspaceId: ctx.workspaceId,
      systemVersionId: req.systemVersionId,
      mode: "ADVISORY_ONLY",
      founderMemberId: memberId,
      technicalOwnerMemberId: req.technicalOwnerMemberId,
    });
  }
);

export const submitAiAssessmentApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/deployments/:deploymentId/assessments", expose: true },
  async (req: SubmitAiAssessmentRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    const memberId = ctx.workforceMemberId || ctx.userId;
    return submitAiAssessment({
      workspaceId: ctx.workspaceId,
      deploymentId: req.deploymentId,
      classification: req.classification,
      intendedPurpose: req.intendedPurpose,
      controls: req.controls,
      affectedStakeholders: req.affectedStakeholders,
      reviewerMemberId: memberId,
      expiresAt: req.expiresAt,
    });
  }
);

export const approveAiAssessmentApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/deployments/:deploymentId/approve", expose: true },
  async (req: ApproveAiAssessmentRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    const memberId = ctx.workforceMemberId || ctx.userId;
    return approveAiAssessment({
      deploymentId: req.deploymentId,
      assessmentId: req.assessmentId,
      approvedByMemberId: memberId,
      rationale: req.rationale,
      expiresAt: req.expiresAt,
    });
  }
);

export const suspendAiDeploymentApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/deployments/:deploymentId/suspend", expose: true },
  async (req: SuspendAiDeploymentRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    const memberId = ctx.workforceMemberId || ctx.userId;
    return suspendAiDeployment({
      deploymentId: req.deploymentId,
      rationale: req.rationale,
      suspendedByMemberId: memberId,
    });
  }
);

export const resumeAiDeploymentApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/deployments/:deploymentId/resume", expose: true },
  async (req: ResumeAiDeploymentRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    const memberId = ctx.workforceMemberId || ctx.userId;
    return resumeAiDeployment({
      deploymentId: req.deploymentId,
      rationale: req.rationale,
      resumedByMemberId: memberId,
    });
  }
);


export const getComplianceCenterViewApi = api(
  { method: "GET", path: "/finance-legal/ai-compliance/center", expose: true },
  async (req: GetComplianceCenterViewRequest): Promise<ComplianceCenterView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return getComplianceCenterView(ctx.workspaceId);
  }
);
