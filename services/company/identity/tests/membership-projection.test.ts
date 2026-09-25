import { describe, it, expect } from "vitest";
import { eq, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createTestWorkspaceWithMember } from "../../operations/tests/_helpers";
import {
  applyMembershipProjection,
  type MembershipProjectionEvent,
} from "../services/membership-projection.service";

const { identityWorkspaceMemberships, identityUserProjections, identityMembershipEventInbox } = schema;

describe("membership projection — versioned, forward-only, idempotent", () => {
  beforeEach(async () => {
    await db.delete(identityMembershipEventInbox);
  });
  it("applies v3 active, v4 revoked, then ignores stale v3 replay", async () => {
    const ws = await createTestWorkspaceWithMember({ role: "member" });
    const platformUserId = `platform-user-${ws.userId}`;

    await db
      .update(identityUserProjections)
      .set({ platformUserId })
      .where(eq(identityUserProjections.id, BigInt(ws.userId)));

    // 1. Event v3 active
    const eventV3: MembershipProjectionEvent = {
      eventId: "evt-v3-active",
      organizationId: ws.workspaceId,
      userId: platformUserId,
      membershipVersion: 3,
      status: "active",
      role: "admin",
      occurredAt: "2026-09-25T10:00:00.000Z",
    };

    const resV3 = await applyMembershipProjection(eventV3);
    expect(resV3.applied).toBe(true);

    const [rowV3] = await db
      .select()
      .from(identityWorkspaceMemberships)
      .where(
        and(
          eq(identityWorkspaceMemberships.workspaceId, BigInt(ws.workspaceId)),
          eq(identityWorkspaceMemberships.userId, BigInt(ws.userId))
        )
      );

    expect(rowV3.membershipState).toBe("active");
    expect(rowV3.sourceMembershipVersion).toBe(3);
    expect(rowV3.role).toBe("admin");
    expect(rowV3.revokedAt).toBeNull();

    // 2. Event v4 revoked
    const eventV4: MembershipProjectionEvent = {
      eventId: "evt-v4-revoked",
      organizationId: ws.workspaceId,
      userId: platformUserId,
      membershipVersion: 4,
      status: "revoked",
      role: "admin",
      occurredAt: "2026-09-25T11:00:00.000Z",
    };

    const resV4 = await applyMembershipProjection(eventV4);
    expect(resV4.applied).toBe(true);

    const [rowV4] = await db
      .select()
      .from(identityWorkspaceMemberships)
      .where(
        and(
          eq(identityWorkspaceMemberships.workspaceId, BigInt(ws.workspaceId)),
          eq(identityWorkspaceMemberships.userId, BigInt(ws.userId))
        )
      );

    expect(rowV4.membershipState).toBe("revoked");
    expect(rowV4.sourceMembershipVersion).toBe(4);
    expect(rowV4.revokedAt).not.toBeNull();

    // 3. Stale v3 replay: MUST NOT reactivate or change role
    const resStaleV3 = await applyMembershipProjection({
      ...eventV3,
      eventId: "evt-v3-replay",
    });
    expect(resStaleV3.applied).toBe(false);
    expect(resStaleV3.reason).toBe("stale_version");

    const [rowAfterStale] = await db
      .select()
      .from(identityWorkspaceMemberships)
      .where(
        and(
          eq(identityWorkspaceMemberships.workspaceId, BigInt(ws.workspaceId)),
          eq(identityWorkspaceMemberships.userId, BigInt(ws.userId))
        )
      );

    expect(rowAfterStale.membershipState).toBe("revoked");
    expect(rowAfterStale.sourceMembershipVersion).toBe(4);
    expect(rowAfterStale.revokedAt).not.toBeNull();

    // 4. Duplicate event id: rejected
    const resDup = await applyMembershipProjection(eventV4);
    expect(resDup.applied).toBe(false);
    expect(resDup.reason).toBe("duplicate_event");

    // 5. Forward re-activation with v5: restores active state
    const eventV5: MembershipProjectionEvent = {
      eventId: "evt-v5-reactivate",
      organizationId: ws.workspaceId,
      userId: platformUserId,
      membershipVersion: 5,
      status: "active",
      role: "founder",
      occurredAt: "2026-09-25T12:00:00.000Z",
    };

    const resV5 = await applyMembershipProjection(eventV5);
    expect(resV5.applied).toBe(true);

    const [rowV5] = await db
      .select()
      .from(identityWorkspaceMemberships)
      .where(
        and(
          eq(identityWorkspaceMemberships.workspaceId, BigInt(ws.workspaceId)),
          eq(identityWorkspaceMemberships.userId, BigInt(ws.userId))
        )
      );

    expect(rowV5.membershipState).toBe("active");
    expect(rowV5.sourceMembershipVersion).toBe(5);
    expect(rowV5.role).toBe("founder");
    expect(rowV5.revokedAt).toBeNull();
  });
});
