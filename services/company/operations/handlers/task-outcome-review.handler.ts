import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  KrContributionView,
  TaskOutcomeReviewView,
  reviewTaskOutcome,
  verifyKrContribution,
} from "../services/task-outcome-review.service";
import {
  WorkPackageReviewView,
  overrideWorkPackagePriority,
  reviewWorkPackage,
} from "../services/work-package-review.service";
import { Priority, WorkPackageView } from "../services/work-package.service";

export const reviewWorkPackageEndpoint = api(
  { method: "POST", path: "/operations/work-packages/:id/review", expose: true },
  async (params: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    workAttemptId?: string;
    artifactVersionRef: string;
    decision: "ACCEPT" | "REWORK" | "REJECT";
    rubricScores: Record<string, number>;
    reasonCode: string;
    narrative?: string;
    expectedVersion: number;
    reworkTargetAgentInstanceId?: string;
  }): Promise<WorkPackageReviewView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return reviewWorkPackage({ ...params, workPackageId: params.id }, ctx);
  }
);

export const overrideWorkPackagePriorityEndpoint = api(
  { method: "POST", path: "/operations/work-packages/:id/priority", expose: true },
  async (params: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    effectivePriority: Priority;
    reason: string;
    expectedVersion: number;
  }): Promise<WorkPackageView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return overrideWorkPackagePriority({ ...params, workPackageId: params.id }, ctx);
  }
);

export const reviewTaskOutcomeEndpoint = api(
  { method: "POST", path: "/operations/task-outcome-reviews", expose: true },
  async (params: {
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    taskResultId: string;
    assessmentId: string;
    decision: "ACCEPT" | "REWORK" | "REJECT";
    expectedResultRevision: number;
    reasonCode: string;
    narrative?: string;
  }): Promise<TaskOutcomeReviewView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return reviewTaskOutcome(params, ctx);
  }
);

export const verifyKrContributionEndpoint = api(
  { method: "POST", path: "/operations/kr-contributions/:id/verify", expose: true },
  async (params: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
    decision: "VERIFIED" | "REJECTED" | "INSUFFICIENT_EVIDENCE";
    reason: string;
    expectedVersion: number;
  }): Promise<KrContributionView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return verifyKrContribution({ ...params, contributionId: params.id }, ctx);
  }
);
