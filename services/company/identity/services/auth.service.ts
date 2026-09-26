import { APIError } from "encore.dev/api";
import { and, asc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import {
  assertSessionAfterRevocation,
  membershipObservation,
  sessionPredatesRevocation,
} from "./membership-reconciliation.service";

const { identityUserProjections, identityWorkspaceMemberships } = schema;

export interface MeResponse {
  id: string;
  email: string | null;
  displayName: string | null;
  workspaceId: string | null;
  role: string | null;
  /** Lần gần nhất membership đang chọn được xác nhận với Core (ISO), null nếu chưa. */
  membershipObservedAt: string | null;
  /** true ⇒ client nên chạy lại /identity/sync-from-platform bằng token Core. */
  membershipObservationStale: boolean;
}

/**
 * Hồ sơ user kèm membership của workspace ĐANG CHỌN (header X-Workspace-Id).
 * Trước đây luôn trả membership active đầu tiên (không ORDER BY), nên user có
 * nhiều workspace nhận nhầm workspace/role và frontend báo "không khớp".
 * Không truyền workspace thì fallback membership active cũ nhất (ổn định).
 */
export async function getMeProfile(
  userIdStr: string,
  workspaceIdStr?: string,
  sessionAuthTime?: number
): Promise<MeResponse> {
  const userId = BigInt(userIdStr);
  const [userRow] = await db
    .select({
      id: identityUserProjections.id,
      email: identityUserProjections.email,
      displayName: identityUserProjections.displayName,
    })
    .from(identityUserProjections)
    .where(eq(identityUserProjections.id, userId))
    .limit(1);

  if (!userRow) throw APIError.notFound("user not found");

  let requestedWorkspaceId: bigint | undefined;
  if (workspaceIdStr && workspaceIdStr.trim() !== "") {
    try {
      requestedWorkspaceId = BigInt(workspaceIdStr.trim());
    } catch {
      throw APIError.invalidArgument("X-Workspace-Id must be a numeric id");
    }
  }

  const [membershipRow] = await db
    .select({
      workspaceId: identityWorkspaceMemberships.workspaceId,
      role: identityWorkspaceMemberships.role,
      sessionNotBefore: identityWorkspaceMemberships.sessionNotBefore,
      syncedAt: identityWorkspaceMemberships.syncedAt,
    })
    .from(identityWorkspaceMemberships)
    .where(
      and(
        eq(identityWorkspaceMemberships.userId, userId),
        eq(identityWorkspaceMemberships.membershipState, "active"),
        requestedWorkspaceId !== undefined
          ? eq(identityWorkspaceMemberships.workspaceId, requestedWorkspaceId)
          : undefined
      )
    )
    .orderBy(asc(identityWorkspaceMemberships.createdAt))
    .limit(1);

  if (requestedWorkspaceId !== undefined && !membershipRow) {
    throw APIError.permissionDenied(`user không thuộc workspace ${workspaceIdStr}`);
  }
  if (membershipRow && requestedWorkspaceId !== undefined) {
    assertSessionAfterRevocation(
      sessionAuthTime,
      membershipRow.sessionNotBefore,
      membershipRow.workspaceId.toString()
    );
  }

  const observation = membershipRow
    ? membershipObservation(membershipRow.syncedAt)
    : { observedAt: null, stale: false };
  return {
    id: userRow.id.toString(),
    email: userRow.email,
    displayName: userRow.displayName,
    workspaceId: membershipRow ? membershipRow.workspaceId.toString() : null,
    role: membershipRow?.role ?? null,
    membershipObservedAt: observation.observedAt,
    membershipObservationStale: observation.stale,
  };
}

// Spec 2026-09-25 §6 — không gia hạn local session cho user mà mọi membership
// đều đã bị Core thu hồi: gia hạn không được kéo dài quyền khi thiếu xác nhận
// active mới. User chưa có membership nào vẫn renew được (không có quyền gì).
// Session epoch (plan 2026-09-25 Task 4): membership active nhưng có mốc thu hồi sau
// auth_time của session cũng không tính — renew không được mở lại quyền đã thu hồi.
export async function assertLocalSessionRenewable(subject: string, sessionAuthTime?: number): Promise<void> {
  if (!/^\d{1,19}$/.test(subject)) return;
  const rows = await db
    .select({
      membershipState: identityWorkspaceMemberships.membershipState,
      sessionNotBefore: identityWorkspaceMemberships.sessionNotBefore,
    })
    .from(identityWorkspaceMemberships)
    .where(eq(identityWorkspaceMemberships.userId, BigInt(subject)));
  const usable = rows.some(
    (row) =>
      row.membershipState === "active" && !sessionPredatesRevocation(sessionAuthTime, row.sessionNotBefore)
  );
  if (rows.length > 0 && !usable) {
    throw APIError.permissionDenied("all workspace memberships have been revoked");
  }
}
