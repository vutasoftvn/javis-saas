import { randomUUID } from "node:crypto";
import { and, eq } from "drizzle-orm";
import { APIError } from "encore.dev/api";
import { db } from "../models/db";
import {
  coreAgentAuthorizationTickets,
  coreWorkspaceAuthorizationStates,
  identityWorkforceMembers,
} from "../../shared/db/schema/identity";
import {
  evaluateAgentCapabilityAuthority,
} from "./agent-authorization.service";
import type { ResourceScope } from "./business-authorization.service";


export interface IssueTicketInput {
  workspaceId: string;
  runId: string;
  toolCallId: string;
  checkpointRef: string;
  capabilityId: string;
  agentWorkforceMemberId: string;
  scope?: ResourceScope;
  facts?: Record<string, unknown>;
}

export interface AuthorizationTicket {
  ticketId: string;
  authorizationEpoch: number;
  expiresAt: string;
}

export interface ExpectedTicketConsumption {
  workspaceId: string;
  runId: string;
  toolCallId: string;
  checkpointRef: string;
  capabilityId: string;
  authorizationEpoch?: number;
}

export async function issueAgentAuthorizationTicket(
  input: IssueTicketInput
): Promise<AuthorizationTicket> {
  const wsId = BigInt(input.workspaceId);
  const agentMemberId = BigInt(input.agentWorkforceMemberId);

  // 1. Verify that agentWorkforceMemberId is active AI_AGENT in workspace
  const [member] = await db
    .select()
    .from(identityWorkforceMembers)
    .where(
      and(
        eq(identityWorkforceMembers.id, agentMemberId),
        eq(identityWorkforceMembers.workspaceId, wsId)
      )
    );

  if (!member || (member.status !== "active" && member.status !== "ACTIVE") || member.memberType !== "AI_AGENT") {
    throw APIError.failedPrecondition(
      `Agent workforce member ${input.agentWorkforceMemberId} is not an active AI_AGENT in workspace ${input.workspaceId}`
    );
  }

  // 2. Evaluate authority
  const evalResult = await evaluateAgentCapabilityAuthority({
    workspaceId: input.workspaceId,
    agentWorkforceMemberId: input.agentWorkforceMemberId,
    capabilityId: input.capabilityId,
    scope: input.scope || { workspaceId: input.workspaceId },
    facts: input.facts || {},
  });


  if (evalResult.effect !== "ALLOW") {
    if (evalResult.reasonCodes.includes("AGENT_CAPABILITY_GRANT_REVOKED")) {
      throw APIError.permissionDenied(
        "AGENT_CAPABILITY_GRANT_REVOKED: agent capability grant has been revoked"
      );
    }
    throw APIError.permissionDenied(
      `Agent capability authority denied: ${evalResult.reasonCodes.join(", ")}`
    );
  }

  // 3. Get current workspace authorization epoch
  const [authEpochState] = await db
    .select()
    .from(coreWorkspaceAuthorizationStates)
    .where(eq(coreWorkspaceAuthorizationStates.workspaceId, wsId));

  const currentEpoch = authEpochState?.authorizationEpoch ?? 1;

  // 4. Create opaque ticket with TTL 60 seconds
  const ticketId = `tkt_${randomUUID().replace(/-/g, "")}`;
  const expiresAt = new Date(Date.now() + 60_000);

  await db.insert(coreAgentAuthorizationTickets).values({
    ticketId,
    workspaceId: wsId,
    runId: input.runId,
    toolCallId: input.toolCallId,
    checkpointRef: input.checkpointRef,
    capabilityId: input.capabilityId,
    agentWorkforceMemberId: agentMemberId,
    authorizationEpoch: currentEpoch,
    status: "ISSUED",
    expiresAt,
  });

  return {
    ticketId,
    authorizationEpoch: currentEpoch,
    expiresAt: expiresAt.toISOString(),
  };
}

export async function consumeAgentAuthorizationTicket(
  tx: any,
  ticketId: string,
  expected: ExpectedTicketConsumption
): Promise<void> {
  const [ticket] = await tx
    .select()
    .from(coreAgentAuthorizationTickets)
    .where(eq(coreAgentAuthorizationTickets.ticketId, ticketId))
    .for("update");

  if (!ticket) {
    throw APIError.notFound("authorization ticket not found");
  }

  if (ticket.status !== "ISSUED") {
    throw APIError.failedPrecondition(
      `authorization ticket already consumed or invalid (status=${ticket.status})`
    );
  }

  if (ticket.expiresAt.getTime() <= Date.now()) {
    await tx
      .update(coreAgentAuthorizationTickets)
      .set({ status: "EXPIRED" })
      .where(eq(coreAgentAuthorizationTickets.ticketId, ticketId));
    throw APIError.failedPrecondition("authorization ticket expired");
  }

  if (ticket.workspaceId.toString() !== expected.workspaceId) {
    throw APIError.permissionDenied("authorization ticket workspace_id mismatch");
  }

  if (ticket.runId !== expected.runId) {
    throw APIError.permissionDenied("authorization ticket run_id mismatch");
  }

  if (ticket.toolCallId !== expected.toolCallId) {
    throw APIError.permissionDenied("authorization ticket tool_call_id mismatch");
  }

  if (ticket.checkpointRef !== expected.checkpointRef) {
    throw APIError.permissionDenied("authorization ticket checkpoint_ref mismatch");
  }

  if (ticket.capabilityId !== expected.capabilityId) {
    throw APIError.permissionDenied("authorization ticket capability_id mismatch");
  }

  if (
    expected.authorizationEpoch !== undefined &&
    ticket.authorizationEpoch !== expected.authorizationEpoch
  ) {
    throw APIError.permissionDenied("authorization ticket epoch mismatch");
  }

  await tx
    .update(coreAgentAuthorizationTickets)
    .set({
      status: "CONSUMED",
      consumedAt: new Date(),
    })
    .where(eq(coreAgentAuthorizationTickets.ticketId, ticketId));
}
