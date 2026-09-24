import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import {
  authorizeAndProjectCoreAccess,
  resolveCallerIdentity,
  syncCoreMembershipsForUser,
} from "./core-access.service";
import {
  listWorkspaceMembershipsForUser,
  validateWorkspaceMembership,
  type WorkspaceMembershipInfo,
} from "./venture-workspace.service";

/**
 * Xác thực thành viên workspace theo bearer token cho các endpoint nội bộ (`/platform/internal/*`)
 * và document-ingestion. Token JWT platform cũ: kiểm tra bảng cục bộ như trước. Token OIDC của core:
 * core quyết định quyền và kết quả được chiếu vào DB COSA trước khi đọc bảng cục bộ.
 */

const { users, profiles } = schema;

export interface TokenMembershipResult {
  userId: string;
  /** null khi user không phải thành viên workspace. */
  membership: WorkspaceMembershipInfo | null;
}

export async function validateMembershipForToken(
  token: string,
  organizationId: string
): Promise<TokenMembershipResult> {
  const caller = await resolveCallerIdentity(token);

  try {
    await authorizeAndProjectCoreAccess(token, organizationId, "cosa.workspace.read");
  } catch (err) {
    if (err instanceof APIError && err.code === "permission_denied") {
      return { userId: caller.userId, membership: null };
    }
    throw err;
  }

  const membership = await validateWorkspaceMembership(BigInt(caller.userId), BigInt(organizationId));
  return { userId: caller.userId, membership };
}

export interface TokenIdentity {
  userId: string;
  email: string | null;
  displayName: string | null;
}

/** Danh tính của người giữ token (JWT platform cũ hoặc token core) cho service khác (services/company). */
export async function resolveIdentityForToken(token: string): Promise<TokenIdentity> {
  const caller = await resolveCallerIdentity(token);
  const [row] = await db
    .select({ email: users.email, fullName: profiles.fullName })
    .from(users)
    .leftJoin(profiles, eq(profiles.id, users.id))
    .where(eq(users.id, BigInt(caller.userId)))
    .limit(1);
  if (!row) {
    throw APIError.notFound("platform user không tồn tại");
  }
  return { userId: caller.userId, email: row.email, displayName: row.fullName };
}

export async function listMembershipsForToken(token: string): Promise<WorkspaceMembershipInfo[]> {
  const caller = await resolveCallerIdentity(token);

  // Core là nguồn sự thật: chiếu lại và chỉ giữ organization còn hiệu lực ở core.
  const liveIds = new Set(await syncCoreMembershipsForUser(token));
  return (await listWorkspaceMembershipsForUser(BigInt(caller.userId))).filter((m) =>
    liveIds.has(m.platformWorkspaceId)
  );
}
