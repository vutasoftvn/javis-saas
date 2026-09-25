import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const {
  identityWorkspaceMemberships,
  identityUserProjections,
  identityMembershipEventInbox,
  identityWorkspaces,
} = schema;

export interface MembershipProjectionEvent {
  eventId: string;
  organizationId: string;
  userId: string;
  membershipVersion: number;
  status: "active" | "revoked" | "deactivated";
  role?: string;
  occurredAt?: string;
}

export interface ApplyMembershipProjectionResult {
  applied: boolean;
  membershipState?: "active" | "revoked";
  version?: number;
  reason?: string;
}

export async function applyMembershipProjection(
  event: MembershipProjectionEvent
): Promise<ApplyMembershipProjectionResult> {
  if (
    !event.eventId ||
    !event.organizationId ||
    !event.userId ||
    event.membershipVersion === undefined ||
    !event.status
  ) {
    throw APIError.invalidArgument("Missing required fields in membership projection event");
  }

  if (!["active", "revoked", "deactivated"].includes(event.status)) {
    throw APIError.invalidArgument(`unsupported membership status ${event.status}`);
  }
  const eventVersion = Number(event.membershipVersion);
  if (!Number.isSafeInteger(eventVersion) || eventVersion < 1) {
    throw APIError.invalidArgument("membershipVersion must be a positive integer");
  }
  if (!/^\d{1,19}$/.test(event.organizationId)) {
    throw APIError.invalidArgument("organizationId must be a numeric id");
  }
  const wsId = BigInt(event.organizationId);
  const now = new Date();
  const occurredAt = event.occurredAt ? new Date(event.occurredAt) : now;
  if (Number.isNaN(occurredAt.getTime())) {
    throw APIError.invalidArgument("occurredAt must be an ISO timestamp");
  }

  return await db.transaction(async (tx) => {
    // 1. Idempotency check via inbox
    const [existingInbox] = await tx
      .select({ eventId: identityMembershipEventInbox.eventId })
      .from(identityMembershipEventInbox)
      .where(eq(identityMembershipEventInbox.eventId, event.eventId))
      .limit(1);

    if (existingInbox) {
      return { applied: false, reason: "duplicate_event" };
    }

    // 2. Find local user projection by platformUserId
    let [user] = await tx
      .select({ id: identityUserProjections.id })
      .from(identityUserProjections)
      .where(eq(identityUserProjections.platformUserId, event.userId))
      .limit(1);

    if (!user) {
      if (event.status === "active") {
        const newUserId = generateSnowflake();
        const [insertedUser] = await tx
          .insert(identityUserProjections)
          .values({
            id: newUserId,
            platformUserId: event.userId,
            displayName: null,
          })
          .onConflictDoNothing()
          .returning({ id: identityUserProjections.id });

        user = insertedUser || (
          await tx
            .select({ id: identityUserProjections.id })
            .from(identityUserProjections)
            .where(eq(identityUserProjections.platformUserId, event.userId))
            .limit(1)
        )[0];
      }
    }

    if (!user) {
      await tx
        .insert(identityMembershipEventInbox)
        .values({
          eventId: event.eventId,
          organizationId: event.organizationId,
          userId: event.userId,
          membershipVersion: eventVersion,
          status: event.status,
          processedAt: now,
        })
        .onConflictDoNothing();

      return { applied: false, reason: "user_not_found" };
    }

    const localUserId = user.id;

    // 3. Find local membership row
    const [membership] = await tx
      .select({
        id: identityWorkspaceMemberships.id,
        role: identityWorkspaceMemberships.role,
        membershipState: identityWorkspaceMemberships.membershipState,
        sourceMembershipVersion: identityWorkspaceMemberships.sourceMembershipVersion,
        revokedAt: identityWorkspaceMemberships.revokedAt,
      })
      .from(identityWorkspaceMemberships)
      .where(
        and(
          eq(identityWorkspaceMemberships.workspaceId, wsId),
          eq(identityWorkspaceMemberships.userId, localUserId)
        )
      )
      .limit(1);

    // 4. If membership exists, check forward-only version
    if (membership) {
      const currentVersion = Number(membership.sourceMembershipVersion ?? 0);
      if (eventVersion <= currentVersion) {
        // Stale or duplicate version: do not apply!
        await tx
          .insert(identityMembershipEventInbox)
          .values({
            eventId: event.eventId,
            organizationId: event.organizationId,
            userId: event.userId,
            membershipVersion: eventVersion,
            status: event.status,
            processedAt: now,
          })
          .onConflictDoNothing();

        return { applied: false, reason: "stale_version" };
      }

      // Newer version: apply forward transition
      const targetState = event.status === "active" ? "active" : "revoked";
      // Tombstone từ sync (không mang version) mới hơn thời điểm event active
      // ⇒ event active này là dữ liệu cũ, không được kích hoạt lại membership.
      if (
        targetState === "active" &&
        membership.membershipState !== "active" &&
        membership.revokedAt &&
        occurredAt.getTime() <= membership.revokedAt.getTime()
      ) {
        await tx
          .insert(identityMembershipEventInbox)
          .values({
            eventId: event.eventId,
            organizationId: event.organizationId,
            userId: event.userId,
            membershipVersion: eventVersion,
            status: event.status,
            processedAt: now,
          })
          .onConflictDoNothing();
        return { applied: false, reason: "stale_after_revocation" };
      }
      const updateValues: Partial<typeof identityWorkspaceMemberships.$inferInsert> = {
        membershipState: targetState,
        sourceMembershipVersion: eventVersion,
        updatedAt: now,
      };

      if (targetState === "active") {
        if (event.role) {
          updateValues.role = event.role;
        }
        updateValues.revokedAt = null;
      } else {
        updateValues.revokedAt = occurredAt;
      }

      await tx
        .update(identityWorkspaceMemberships)
        .set(updateValues)
        .where(eq(identityWorkspaceMemberships.id, membership.id));

      await tx
        .insert(identityMembershipEventInbox)
        .values({
          eventId: event.eventId,
          organizationId: event.organizationId,
          userId: event.userId,
          membershipVersion: eventVersion,
          status: event.status,
          processedAt: now,
        })
        .onConflictDoNothing();

      return {
        applied: true,
        membershipState: targetState,
        version: eventVersion,
      };
    } else {
      if (event.status === "active") {
        await tx
          .insert(identityWorkspaces)
          .values({
            id: wsId,
            name: `Workspace ${event.organizationId}`,
            platformWorkspaceId: event.organizationId,
            lifecycleStage: "W0_IDEA",
            stageEnteredAt: now,
          })
          .onConflictDoNothing();

        await tx.insert(identityWorkspaceMemberships).values({
          id: generateSnowflake(),
          workspaceId: wsId,
          userId: localUserId,
          role: event.role || "member",
          membershipState: "active",
          sourceMembershipVersion: eventVersion,
          syncedAt: now,
          updatedAt: now,
        });

        await tx
          .insert(identityMembershipEventInbox)
          .values({
            eventId: event.eventId,
            organizationId: event.organizationId,
            userId: event.userId,
            membershipVersion: eventVersion,
            status: event.status,
            processedAt: now,
          })
          .onConflictDoNothing();

        return {
          applied: true,
          membershipState: "active",
          version: eventVersion,
        };
      } else {
        await tx
          .insert(identityMembershipEventInbox)
          .values({
            eventId: event.eventId,
            organizationId: event.organizationId,
            userId: event.userId,
            membershipVersion: eventVersion,
            status: event.status,
            processedAt: now,
          })
          .onConflictDoNothing();

        return { applied: false, reason: "membership_not_found" };
      }
    }
  });
}
