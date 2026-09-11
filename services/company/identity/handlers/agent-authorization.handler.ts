import { api, Header, APIError } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  grantAgentCapability,
  revokeAgentCapability,
  getAuthorizationOverview,
  evaluateAgentCapabilityAuthority,
} from "../services/agent-authorization.service";
import { ResourceScope, RuleDecision } from "../services/business-authorization.service";

export interface GetAuthorizationOverviewApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export interface GrantAgentCapabilityApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  agentWorkforceMemberId: string;
  capabilityId: string;
  projectId?: string;
  legalEntityId?: string;
  constraints?: Record<string, unknown>;
  validUntil?: string;
}

export interface RevokeAgentCapabilityApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  grantId: string;
  reason: string;
}

export interface SimulateAgentAuthorizationApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  agentWorkforceMemberId: string;
  capabilityId: string;
  scope?: ResourceScope;
  facts?: Record<string, unknown>;
}

export const getAuthorizationOverviewEndpoint = api(
  { method: "GET", path: "/identity/authorization/overview", expose: true },
  async (req: GetAuthorizationOverviewApiRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return getAuthorizationOverview(ctx);
  }
);

export const createAgentCapabilityGrantEndpoint = api(
  { method: "POST", path: "/identity/agent-capability-grants", expose: true },
  async (req: GrantAgentCapabilityApiRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return grantAgentCapability(ctx, {
      workspaceId: ctx.workspaceId,
      agentWorkforceMemberId: req.agentWorkforceMemberId,
      capabilityId: req.capabilityId,
      projectId: req.projectId,
      legalEntityId: req.legalEntityId,
      constraints: req.constraints,
      validUntil: req.validUntil,
    });
  }
);

export const revokeAgentCapabilityGrantEndpoint = api(
  { method: "POST", path: "/identity/agent-capability-grants/:grantId/revoke", expose: true },
  async (req: RevokeAgentCapabilityApiRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return revokeAgentCapability(ctx, {
      grantId: req.grantId,
      reason: req.reason,
    });
  }
);

export const simulateAgentAuthorizationEndpoint = api(
  { method: "POST", path: "/identity/authorization/simulate", expose: true },
  async (req: SimulateAgentAuthorizationApiRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return evaluateAgentCapabilityAuthority({
      workspaceId: ctx.workspaceId,
      agentWorkforceMemberId: req.agentWorkforceMemberId,
      capabilityId: req.capabilityId,
      scope: {
        workspaceId: ctx.workspaceId,
        projectId: req.scope?.projectId,
        legalEntityId: req.scope?.legalEntityId,
      },
      facts: req.facts || {},
    });
  }
);

export interface IssueAgentAuthorizationTicketApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  runId: string;
  toolCallId: string;
  checkpointRef: string;
  capabilityId: string;
  agentWorkforceMemberId: string;
  scope?: ResourceScope;
  facts?: Record<string, unknown>;
}


export const issueAgentAuthorizationTicketEndpoint = api(
  { method: "POST", path: "/identity/agent-authorization/tickets", expose: true },
  async (req: IssueAgentAuthorizationTicketApiRequest) => {
    const rawToken = (req.authorization || "").replace(/^Bearer\s+/i, "");
    if (!rawToken) {
      throw APIError.unauthenticated("missing authorization delegation token");
    }

    // Verify COSA delegation token
    const { verifyCosaDelegation } = await import("../../shared/auth/cosa-delegation.service");
    try {
      verifyCosaDelegation(rawToken, {
        workspaceId: req.workspaceId,
        runId: req.runId,
        capabilityId: req.capabilityId,
      });
    } catch (err) {
      // Fallback: if caller is authenticated human founder with workspace access, allow ticket issuance for testing
      const { requireWorkspaceAccess } = await import("../../shared/auth/workspace-access");
      try {
        await requireWorkspaceAccess(req.authorization, req.workspaceId);
      } catch {
        throw APIError.permissionDenied((err as Error).message);
      }
    }

    const { issueAgentAuthorizationTicket } = await import("../services/agent-authorization-ticket.service");
    return issueAgentAuthorizationTicket({
      workspaceId: req.workspaceId,
      runId: req.runId,
      toolCallId: req.toolCallId,
      checkpointRef: req.checkpointRef,
      capabilityId: req.capabilityId,
      agentWorkforceMemberId: req.agentWorkforceMemberId,
      scope: req.scope,
      facts: req.facts,
    });
  }
);

