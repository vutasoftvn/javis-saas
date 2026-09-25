import { describe, expect, it } from "vitest";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { resolveTenantContext } from "../services/tenant-context.service";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { applyMembershipProjection } from "../services/membership-projection.service";
import { ingestMembershipEvent } from "../handlers/membership-event.handler";
import { mintTestWorkerToken } from "../../shared/auth/worker-service-auth";

const { identityWorkspaceMemberships, identityUserProjections } = schema;

// Spec 2026-09-25 §6 — membership bị Core thu hồi phải chặn local session ngay,
// và event cũ không bao giờ kích hoạt lại được membership đã tombstone.

async function linkPlatformUser(userId: string): Promise<string> {
  const platformUserId = `platform-user-${userId}`;
  await db
    .update(identityUserProjections)
    .set({ platformUserId })
    .where(eq(identityUserProjections.id, BigInt(userId)));
  return platformUserId;
}

async function readMembership(workspaceId: string, userId: string) {
  const [row] = await db
    .select()
    .from(identityWorkspaceMemberships)
    .where(
      and(
        eq(identityWorkspaceMemberships.workspaceId, BigInt(workspaceId)),
        eq(identityWorkspaceMemberships.userId, BigInt(userId))
      )
    );
  return row;
}

describe("membership revocation enforcement", () => {
  it("denies a still-valid local session once Core revokes the membership", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const platformUserId = await linkPlatformUser(ws.userId);

    const before = await resolveTenantContext({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
    });
    expect(before.membershipRole).toBe("founder");

    const res = await applyMembershipProjection({
      eventId: `evt-revoke-${ws.userId}`,
      organizationId: ws.workspaceId,
      userId: platformUserId,
      membershipVersion: 2,
      status: "revoked",
      occurredAt: new Date().toISOString(),
    });
    expect(res).toMatchObject({ applied: true, membershipState: "revoked" });

    await expect(
      resolveTenantContext({ authorization: ws.bearerToken, workspaceId: ws.workspaceId })
    ).rejects.toMatchObject({ code: "permission_denied" });
    await expect(
      requireWorkspaceAccess(ws.bearerToken, ws.workspaceId)
    ).rejects.toMatchObject({ code: "permission_denied" });
  });

  it("does not reactivate a sync tombstone from an older active event", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    const platformUserId = await linkPlatformUser(ws.userId);
    const revokedAt = new Date();

    // Tombstone do sync ghi (không mang version mới).
    await db
      .update(identityWorkspaceMemberships)
      .set({ membershipState: "revoked", revokedAt })
      .where(
        and(
          eq(identityWorkspaceMemberships.workspaceId, BigInt(ws.workspaceId)),
          eq(identityWorkspaceMemberships.userId, BigInt(ws.userId))
        )
      );

    const res = await applyMembershipProjection({
      eventId: `evt-stale-active-${ws.userId}`,
      organizationId: ws.workspaceId,
      userId: platformUserId,
      membershipVersion: 2,
      status: "active",
      occurredAt: new Date(revokedAt.getTime() - 60_000).toISOString(),
    });
    expect(res).toMatchObject({ applied: false, reason: "stale_after_revocation" });
    expect((await readMembership(ws.workspaceId, ws.userId)).membershipState).toBe("revoked");
  });

  it("rejects malformed events before touching the projection", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    await expect(
      applyMembershipProjection({
        eventId: `evt-bad-${ws.userId}`,
        organizationId: ws.workspaceId,
        userId: "platform-user-x",
        membershipVersion: 0,
        status: "revoked",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
    await expect(
      applyMembershipProjection({
        eventId: `evt-bad-org-${ws.userId}`,
        organizationId: "not-a-number",
        userId: "platform-user-x",
        membershipVersion: 3,
        status: "revoked",
      })
    ).rejects.toMatchObject({ code: "invalid_argument" });
  });
});

describe("POST /internal/identity/membership-events", () => {
  it("rejects the legacy static token and requests without credentials", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    const event = {
      eventId: `evt-auth-${ws.userId}`,
      organizationId: ws.workspaceId,
      userId: "platform-user-x",
      membershipVersion: 5,
      status: "revoked" as const,
    };
    await expect(ingestMembershipEvent({ event })).rejects.toMatchObject({
      code: "unauthenticated",
    });
    await expect(
      ingestMembershipEvent({ event, serviceToken: "dev-worker-service-token" })
    ).rejects.toMatchObject({ code: "unauthenticated" });
  });

  it("applies a revocation with a valid worker token", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    const platformUserId = await linkPlatformUser(ws.userId);
    const res = await ingestMembershipEvent({
      event: {
        eventId: `evt-handler-${ws.userId}`,
        organizationId: ws.workspaceId,
        userId: platformUserId,
        membershipVersion: 7,
        status: "revoked",
        occurredAt: new Date().toISOString(),
      },
      authorization: `Bearer ${mintTestWorkerToken("membership-relay")}`,
    });
    expect(res).toMatchObject({ applied: true, membershipState: "revoked", version: 7 });
    expect((await readMembership(ws.workspaceId, ws.userId)).membershipState).toBe("revoked");
  });
});
