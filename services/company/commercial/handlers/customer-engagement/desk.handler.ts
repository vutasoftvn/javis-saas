import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  ENGAGEMENT_PERMISSIONS,
  requireEngagementPermission,
} from "../../services/customer-engagement/rbac";
import {
  changeThreadStatus,
  getThread,
  listThreads,
  openThread,
} from "../../services/customer-engagement/thread.service";
import {
  postInternalNote,
  sendPublicMessage,
} from "../../services/customer-engagement/message.service";
import {
  assignThread,
  handBackToAgent,
  takeOverThread,
} from "../../services/customer-engagement/assignment.service";
import { getCustomer360 } from "../../services/customer-engagement/customer360.service";
import { setEscalationRoute } from "../../services/customer-engagement/escalation.service";
import {
  grantAuthorityCapability,
  seedDecisionAuthority,
  type ApprovalPolicy,
} from "../../services/customer-engagement/decision-authority.service";
import {
  createDecisionRequest,
  executeDecisionRequest,
  recordApproval,
  startReview,
  submitDecisionRequest,
} from "../../services/customer-engagement/decision-request.service";

interface WorkspaceRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

async function workspaceContext(params: WorkspaceRequest) {
  return requireWorkspaceAccess(params.authorization, params.workspaceId);
}

export interface CreateEngagementThreadRequest extends WorkspaceRequest {
  inboxId: string;
  contactId?: string;
  priority?: string;
  tier?: string;
  correlationId?: string;
}

export const createEngagementThreadApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/threads" },
  async (params: CreateEngagementThreadRequest) => {
    const ctx = await workspaceContext(params);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_WRITE);
    return openThread({ ...params, workspaceId: ctx.workspaceId }, ctx);
  },
);

export interface GetEngagementThreadRequest extends WorkspaceRequest {
  id: string;
}

export const getEngagementThreadApi = api(
  { expose: true, method: "GET", path: "/commercial/engagement/threads/:id" },
  async (params: GetEngagementThreadRequest) => {
    const ctx = await workspaceContext(params);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_READ);
    return getThread(params.id, ctx);
  },
);

export interface ListEngagementThreadsRequest extends WorkspaceRequest {
  status?: string;
  priority?: string;
  ownerMemberId?: string;
  activeMode?: string;
  limit?: number;
}

export const listEngagementThreadsApi = api(
  { expose: true, method: "GET", path: "/commercial/engagement/threads" },
  async (params: ListEngagementThreadsRequest) => {
    const ctx = await workspaceContext(params);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_READ);
    return {
      threads: await listThreads(params, ctx),
    };
  },
);

export interface ChangeEngagementThreadStatusRequest extends WorkspaceRequest {
  id: string;
  to: "open" | "pending_customer" | "pending_internal" | "snoozed" | "resolved";
  reasonCode: string;
  snoozedUntil?: string;
  resolutionCode?: string;
}

export const changeEngagementThreadStatusApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/threads/:id/status" },
  async ({ id, workspaceId, authorization, ...params }: ChangeEngagementThreadStatusRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_WRITE);
    return changeThreadStatus(id, params, ctx);
  },
);

export interface SendEngagementMessageRequest extends WorkspaceRequest {
  id: string;
  body: string;
  idempotencyKey: string;
}

export const postEngagementInternalNoteApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/threads/:id/notes" },
  async ({ id, workspaceId, authorization, body, idempotencyKey }: SendEngagementMessageRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_WRITE);
    return postInternalNote({ threadId: id, body, idempotencyKey }, ctx);
  },
);

export const sendEngagementPublicMessageApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/threads/:id/messages" },
  async ({ id, workspaceId, authorization, body, idempotencyKey }: SendEngagementMessageRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.MESSAGE_SEND);
    return sendPublicMessage({ threadId: id, body, idempotencyKey }, ctx);
  },
);

export interface AssignEngagementThreadRequest extends WorkspaceRequest {
  id: string;
  teamId?: string;
  memberId?: string;
  agentSpecId?: string;
  reason: string;
}

export const assignEngagementThreadApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/threads/:id/assign" },
  async ({ id, workspaceId, authorization, teamId, memberId, agentSpecId, reason }: AssignEngagementThreadRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_WRITE);
    return assignThread({ threadId: id, teamId, memberId, agentSpecId, reason }, ctx);
  },
);

export interface TakeOverEngagementThreadRequest extends WorkspaceRequest {
  id: string;
  reason: string;
}

export const takeOverEngagementThreadApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/threads/:id/takeover" },
  async ({ id, workspaceId, authorization, reason }: TakeOverEngagementThreadRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    return takeOverThread({ threadId: id, reason }, ctx);
  },
);

export interface HandBackEngagementThreadRequest extends WorkspaceRequest {
  id: string;
  agentSpecId: string;
  scope?: string;
  expiresAt: string;
}

export const handBackEngagementThreadApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/threads/:id/hand-back" },
  async ({ id, workspaceId, authorization, agentSpecId, scope, expiresAt }: HandBackEngagementThreadRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_WRITE);
    return handBackToAgent({ threadId: id, agentSpecId, scope, expiresAt }, ctx);
  },
);

export interface GetCustomer360Request extends WorkspaceRequest {
  id: string;
}

export const getEngagementCustomer360Api = api(
  { expose: true, method: "GET", path: "/commercial/engagement/contacts/:id/360" },
  async (params: GetCustomer360Request) => {
    const ctx = await workspaceContext(params);
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_READ);
    // The desk endpoint deliberately returns the identity-unverified view.
    // Customer-sensitive billing and interaction data stays unavailable until
    // a channel-specific identity proof flow supplies stronger evidence.
    return getCustomer360(params.id, ctx, { identityVerified: false });
  },
);

export interface SetEngagementEscalationRouteRequest extends WorkspaceRequest {
  routeKey: string;
  role: "primary" | "backup" | "duty_manager";
  workforceMemberId: string;
  activeUntil?: string;
}

export const setEngagementEscalationRouteApi = api(
  { expose: true, method: "PUT", path: "/commercial/engagement/escalation-routes/:routeKey" },
  async ({ workspaceId, authorization, routeKey, role, workforceMemberId, activeUntil }: SetEngagementEscalationRouteRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.escalationRouteManage);
    await setEscalationRoute({
      workspaceId: ctx.workspaceId,
      routeKey,
      role,
      workforceMemberId,
      activeUntil: activeUntil ? new Date(activeUntil) : undefined,
    }, ctx);
    return { success: true };
  },
);

export interface CreateDecisionAuthorityRequest extends WorkspaceRequest {
  authorityKey: string;
  decisionKind: string;
  matchCriteria?: Record<string, unknown>;
  approvalPolicy: ApprovalPolicy;
}

export const createDecisionAuthorityApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/decision-authorities" },
  async ({ workspaceId, authorization, authorityKey, decisionKind, matchCriteria, approvalPolicy }: CreateDecisionAuthorityRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.decisionAuthorityManage);
    return seedDecisionAuthority({
      workspaceId: ctx.workspaceId,
      authorityKey,
      decisionKind,
      matchCriteria,
      approvalPolicy,
    }, ctx);
  },
);

export interface GrantDecisionAuthorityCapabilityRequest extends WorkspaceRequest {
  authorityKey: string;
  workforceMemberId: string;
  capability: string;
  activeUntil?: string;
}

export const grantDecisionAuthorityCapabilityApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/decision-authorities/:authorityKey/grants" },
  async ({ workspaceId, authorization, authorityKey, workforceMemberId, capability, activeUntil }: GrantDecisionAuthorityCapabilityRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.decisionAuthorityManage);
    await grantAuthorityCapability({
      workspaceId: ctx.workspaceId,
      authorityKey,
      workforceMemberId,
      capability,
      activeUntil: activeUntil ? new Date(activeUntil) : undefined,
    }, ctx);
    return { success: true };
  },
);

export interface CreateDecisionRequestApiRequest extends WorkspaceRequest {
  threadId?: string;
  requestType: string;
  contactId?: string;
  accountId?: string;
  leadId?: string;
  opportunityId?: string;
  customerId?: string;
  options?: unknown[];
  factsRef?: string;
  recommendationRef?: string;
  authorityKey: string;
}

export const createDecisionRequestApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/decision-requests" },
  async ({ workspaceId, authorization, ...params }: CreateDecisionRequestApiRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_WRITE);
    return createDecisionRequest(params, ctx);
  },
);

export interface SubmitDecisionRequestApiRequest extends WorkspaceRequest {
  id: string;
  policyId?: string;
  policyVersion?: string;
  policySnapshotRef: string;
}

export const submitDecisionRequestApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/decision-requests/:id/submit" },
  async ({ id, workspaceId, authorization, policyId, policyVersion, policySnapshotRef }: SubmitDecisionRequestApiRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    requireEngagementPermission(ctx, ENGAGEMENT_PERMISSIONS.THREAD_WRITE);
    return submitDecisionRequest(id, { policyId, policyVersion, policySnapshotRef }, ctx);
  },
);

export const startDecisionReviewApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/decision-requests/:id/review" },
  async ({ id, workspaceId, authorization }: GetEngagementThreadRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    return startReview(id, ctx);
  },
);

export interface RecordDecisionApprovalApiRequest extends WorkspaceRequest {
  id: string;
  decision: "approve" | "reject" | "needs_information";
  reason?: string;
}

export const recordDecisionApprovalApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/decision-requests/:id/approvals" },
  async ({ id, workspaceId, authorization, decision, reason }: RecordDecisionApprovalApiRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    return recordApproval(id, { decision, reason }, ctx);
  },
);

export const executeDecisionRequestApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/decision-requests/:id/execute" },
  async ({ id, workspaceId, authorization }: GetEngagementThreadRequest) => {
    const ctx = await workspaceContext({ workspaceId, authorization });
    return executeDecisionRequest(id, ctx);
  },
);
