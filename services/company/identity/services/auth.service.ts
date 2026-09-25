import { APIError } from "encore.dev/api";
import { and, asc, eq } from "drizzle-orm";
import { db, schema } from "../models/db";

const { identityUserProjections, identityWorkspaceMemberships } = schema;

export interface MeResponse {
  id: string;
  email: string | null;
  displayName: string | null;
  workspaceId: string | null;
  role: string | null;
}

/**
 * Hồ sơ user kèm membership của workspace ĐANG CHỌN (header X-Workspace-Id).
 * Trước đây luôn trả membership active đầu tiên (không ORDER BY), nên user có
 * nhiều workspace nhận nhầm workspace/role và frontend báo "không khớp".
 * Không truyền workspace thì fallback membership active cũ nhất (ổn định).
 */
export async function getMeProfile(userIdStr: string, workspaceIdStr?: string): Promise<MeResponse> {
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

  return {
    id: userRow.id.toString(),
    email: userRow.email,
    displayName: userRow.displayName,
    workspaceId: membershipRow ? membershipRow.workspaceId.toString() : null,
    role: membershipRow?.role ?? null,
  };
}

// Spec 2026-09-25 §6 — không gia hạn local session cho user mà mọi membership
// đều đã bị Core thu hồi: gia hạn không được kéo dài quyền khi thiếu xác nhận
// active mới. User chưa có membership nào vẫn renew được (không có quyền gì).
export async function assertLocalSessionRenewable(subject: string): Promise<void> {
  if (!/^\d{1,19}$/.test(subject)) return;
  const rows = await db
    .select({ membershipState: identityWorkspaceMemberships.membershipState })
    .from(identityWorkspaceMemberships)
    .where(eq(identityWorkspaceMemberships.userId, BigInt(subject)));
  if (rows.length > 0 && !rows.some((row) => row.membershipState === "active")) {
    throw APIError.permissionDenied("all workspace memberships have been revoked");
  }
}
