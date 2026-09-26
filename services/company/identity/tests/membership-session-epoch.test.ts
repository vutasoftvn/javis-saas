import { describe, expect, it } from "vitest";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { applyMembershipProjection } from "../services/membership-projection.service";
import { assertLocalSessionRenewable, getMeProfile } from "../services/auth.service";
import { signAccessToken } from "../services/token.service";
import {
  membershipObservation,
  revocationValues,
  sessionPredatesRevocation,
} from "../services/membership-reconciliation.service";

const { identityWorkspaceMemberships, identityUserProjections } = schema;

// Plan 2026-09-25 core-auth Task 4: session epoch — local session cấp trước lần
// thu hồi không lấy lại quyền khi membership được cấp lại; renew không mở lại quyền;
// /identity/me báo membership đã quá tuổi quan sát để client đồng bộ lại với Core.

async function linkPlatformUser(userId: string): Promise<string> {
  const platformUserId = `platform-epoch-${userId}`;
  await db
    .update(identityUserProjections)
    .set({ platformUserId })
    .where(eq(identityUserProjections.id, BigInt(userId)));
  return platformUserId;
}

async function membershipRow(workspaceId: string, userId: string) {
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

const nowSeconds = () => Math.floor(Date.now() / 1000);

describe("session epoch helpers", () => {
  it("treats sessions issued at or before the revocation second as stale", () => {
    const revokedAt = new Date("2026-09-26T10:00:00.500Z");
    const revokedSecond = Math.floor(revokedAt.getTime() / 1000);
    expect(sessionPredatesRevocation(revokedSecond - 1, revokedAt)).toBe(true);
    expect(sessionPredatesRevocation(revokedSecond, revokedAt)).toBe(true);
    expect(sessionPredatesRevocation(revokedSecond + 1, revokedAt)).toBe(false);
    expect(sessionPredatesRevocation(undefined, revokedAt)).toBe(true);
    expect(sessionPredatesRevocation(undefined, null)).toBe(false);
  });

  it("tombstone values always move the session epoch forward", () => {
    const now = new Date();
    expect(revocationValues(now)).toEqual({
      membershipState: "revoked",
      revokedAt: now,
      sessionNotBefore: now,
      updatedAt: now,
    });
  });

  it("reports a membership never confirmed with Core, or confirmed too long ago, as stale", () => {
    const now = Date.parse("2026-09-26T12:00:00Z");
    expect(membershipObservation(null, now)).toEqual({ observedAt: null, stale: true });
    expect(membershipObservation(new Date(now - 60_000), now).stale).toBe(false);
    expect(membershipObservation(new Date(now - 13 * 3600_000), now).stale).toBe(true);
  });
});

describe("revoked then re-granted membership", () => {
  it("keeps denying the pre-revocation session while a fresh session works", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "founder" });
    const platformUserId = await linkPlatformUser(ws.userId);
    const oldSession = `Bearer ${signAccessToken(ws.userId, nowSeconds() - 120)}`;

    await expect(requireWorkspaceAccess(oldSession, ws.workspaceId)).resolves.toBeDefined();

    await applyMembershipProjection({
      eventId: `evt-epoch-revoke-${ws.userId}`,
      organizationId: ws.workspaceId,
      userId: platformUserId,
      membershipVersion: 2,
      status: "revoked",
      occurredAt: new Date().toISOString(),
    });
    const regrant = await applyMembershipProjection({
      eventId: `evt-epoch-regrant-${ws.userId}`,
      organizationId: ws.workspaceId,
      userId: platformUserId,
      membershipVersion: 3,
      status: "active",
      role: "founder",
      occurredAt: new Date(Date.now() + 1000).toISOString(),
    });
    expect(regrant).toMatchObject({ applied: true, membershipState: "active" });

    const row = await membershipRow(ws.workspaceId, ws.userId);
    expect(row.membershipState).toBe("active");
    expect(row.sessionNotBefore).not.toBeNull();

    // Session cũ không sống lại dù membership đã active trở lại.
    await expect(requireWorkspaceAccess(oldSession, ws.workspaceId)).rejects.toMatchObject({
      code: "permission_denied",
    });
    await expect(getMeProfile(ws.userId, ws.workspaceId, nowSeconds() - 120)).rejects.toMatchObject({
      code: "permission_denied",
    });
    await expect(assertLocalSessionRenewable(ws.userId, nowSeconds() - 120)).rejects.toMatchObject({
      code: "permission_denied",
    });

    // Session mới (đồng bộ lại với Core sau khi cấp lại) dùng được.
    const freshAuthTime = Math.floor(row.sessionNotBefore!.getTime() / 1000) + 1;
    const freshSession = `Bearer ${signAccessToken(ws.userId, freshAuthTime)}`;
    await expect(requireWorkspaceAccess(freshSession, ws.workspaceId)).resolves.toMatchObject({
      workspaceId: ws.workspaceId,
    });
    await expect(assertLocalSessionRenewable(ws.userId, freshAuthTime)).resolves.toBeUndefined();
  });
});

describe("/identity/me membership observation", () => {
  it("flags a membership that was never confirmed with Core and clears it after a Core event", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    const platformUserId = await linkPlatformUser(ws.userId);
    await db
      .update(identityWorkspaceMemberships)
      .set({ syncedAt: null })
      .where(
        and(
          eq(identityWorkspaceMemberships.workspaceId, BigInt(ws.workspaceId)),
          eq(identityWorkspaceMemberships.userId, BigInt(ws.userId))
        )
      );

    const before = await getMeProfile(ws.userId, ws.workspaceId, nowSeconds());
    expect(before).toMatchObject({ membershipObservedAt: null, membershipObservationStale: true });

    await applyMembershipProjection({
      eventId: `evt-observe-${ws.userId}`,
      organizationId: ws.workspaceId,
      userId: platformUserId,
      membershipVersion: 2,
      status: "active",
      role: "member",
      occurredAt: new Date().toISOString(),
    });
    const after = await getMeProfile(ws.userId, ws.workspaceId, nowSeconds());
    expect(after.membershipObservationStale).toBe(false);
    expect(after.membershipObservedAt).not.toBeNull();
  });
});
