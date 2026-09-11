import { describe, expect, it } from "vitest";
import { eq } from "drizzle-orm";
import { db } from "../models/db";
import {
  coreAgentAuthorizationTickets,
  coreAgentCapabilityGrants,
} from "../../shared/db/schema/identity";
import { seedAgentAuthorityWorkspace } from "./agent-authorization.test";
import {
  issueAgentAuthorizationTicket,
  consumeAgentAuthorizationTicket,
} from "../services/agent-authorization-ticket.service";

describe("agent-authorization-ticket.service", () => {
  it("issues an opaque live ticket for an active capability grant", async () => {
    const seed = await seedAgentAuthorityWorkspace({ capabilityId: "finance.transaction.record" });

    // Insert active grant
    await db.insert(coreAgentCapabilityGrants).values({
      workspaceId: BigInt(seed.workspaceId),
      agentWorkforceMemberId: BigInt(seed.agentMemberId),
      capabilityId: "finance.transaction.record",
      status: "ACTIVE",
      grantedByFounderMemberId: BigInt(seed.founderMemberId),
    });

    const ticket = await issueAgentAuthorizationTicket({
      workspaceId: seed.workspaceId,
      runId: "run-live-1",
      toolCallId: "call-1",
      checkpointRef: "ckpt-1",
      capabilityId: "finance.transaction.record",
      agentWorkforceMemberId: seed.agentMemberId,
    });

    expect(ticket.ticketId).toMatch(/^tkt_/);
    expect(ticket.authorizationEpoch).toBeGreaterThanOrEqual(1);
    expect(new Date(ticket.expiresAt).getTime()).toBeGreaterThan(Date.now());
    expect(new Date(ticket.expiresAt).getTime() - Date.now()).toBeLessThanOrEqual(60_000);

    // Verify persisted record
    const [record] = await db
      .select()
      .from(coreAgentAuthorizationTickets)
      .where(eq(coreAgentAuthorizationTickets.ticketId, ticket.ticketId));

    expect(record).toBeDefined();
    expect(record.status).toBe("ISSUED");
    expect(record.runId).toBe("run-live-1");
  });

  it("fails to issue a ticket when grant is revoked", async () => {
    const seed = await seedAgentAuthorityWorkspace({ capabilityId: "finance.transaction.record" });

    // Insert revoked grant
    await db.insert(coreAgentCapabilityGrants).values({
      workspaceId: BigInt(seed.workspaceId),
      agentWorkforceMemberId: BigInt(seed.agentMemberId),
      capabilityId: "finance.transaction.record",
      status: "REVOKED",
      revokedAt: new Date(),
      revokeReason: "Security review",
      grantedByFounderMemberId: BigInt(seed.founderMemberId),
    });

    await expect(
      issueAgentAuthorizationTicket({
        workspaceId: seed.workspaceId,
        runId: "run-live-2",
        toolCallId: "call-2",
        checkpointRef: "ckpt-2",
        capabilityId: "finance.transaction.record",
        agentWorkforceMemberId: seed.agentMemberId,
      })
    ).rejects.toThrow(/AGENT_CAPABILITY_GRANT_REVOKED/);
  });

  it("consumes an issued ticket in a transaction and prevents replay", async () => {
    const seed = await seedAgentAuthorityWorkspace({ capabilityId: "finance.transaction.record" });

    await db.insert(coreAgentCapabilityGrants).values({
      workspaceId: BigInt(seed.workspaceId),
      agentWorkforceMemberId: BigInt(seed.agentMemberId),
      capabilityId: "finance.transaction.record",
      status: "ACTIVE",
      grantedByFounderMemberId: BigInt(seed.founderMemberId),
    });

    const ticket = await issueAgentAuthorizationTicket({
      workspaceId: seed.workspaceId,
      runId: "run-live-3",
      toolCallId: "call-3",
      checkpointRef: "ckpt-3",
      capabilityId: "finance.transaction.record",
      agentWorkforceMemberId: seed.agentMemberId,
    });

    // First consumption succeeds
    await db.transaction(async (tx) => {
      await consumeAgentAuthorizationTicket(tx, ticket.ticketId, {
        workspaceId: seed.workspaceId,
        runId: "run-live-3",
        toolCallId: "call-3",
        checkpointRef: "ckpt-3",
        capabilityId: "finance.transaction.record",
        authorizationEpoch: ticket.authorizationEpoch,
      });
    });

    // Verify status is CONSUMED
    const [record] = await db
      .select()
      .from(coreAgentAuthorizationTickets)
      .where(eq(coreAgentAuthorizationTickets.ticketId, ticket.ticketId));
    expect(record.status).toBe("CONSUMED");
    expect(record.consumedAt).toBeDefined();

    // Second consumption (replay) must throw
    await expect(
      db.transaction(async (tx) => {
        await consumeAgentAuthorizationTicket(tx, ticket.ticketId, {
          workspaceId: seed.workspaceId,
          runId: "run-live-3",
          toolCallId: "call-3",
          checkpointRef: "ckpt-3",
          capabilityId: "finance.transaction.record",
          authorizationEpoch: ticket.authorizationEpoch,
        });
      })
    ).rejects.toThrow(/already consumed/);
  });

  it("rejects consuming ticket if runId or capabilityId mismatches", async () => {
    const seed = await seedAgentAuthorityWorkspace({ capabilityId: "finance.transaction.record" });

    await db.insert(coreAgentCapabilityGrants).values({
      workspaceId: BigInt(seed.workspaceId),
      agentWorkforceMemberId: BigInt(seed.agentMemberId),
      capabilityId: "finance.transaction.record",
      status: "ACTIVE",
      grantedByFounderMemberId: BigInt(seed.founderMemberId),
    });

    const ticket = await issueAgentAuthorizationTicket({
      workspaceId: seed.workspaceId,
      runId: "run-live-4",
      toolCallId: "call-4",
      checkpointRef: "ckpt-4",
      capabilityId: "finance.transaction.record",
      agentWorkforceMemberId: seed.agentMemberId,
    });

    await expect(
      db.transaction(async (tx) => {
        await consumeAgentAuthorizationTicket(tx, ticket.ticketId, {
          workspaceId: seed.workspaceId,
          runId: "different-run",
          toolCallId: "call-4",
          checkpointRef: "ckpt-4",
          capabilityId: "finance.transaction.record",
          authorizationEpoch: ticket.authorizationEpoch,
        });
      })
    ).rejects.toThrow(/mismatch/);
  });
});
