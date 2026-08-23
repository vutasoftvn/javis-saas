import { APIError } from "encore.dev/api";
import { eq, sql, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { signAccessToken } from "./token.service";
import { validatePlatformMembership } from "./platform.client";

// Đồng bộ một chiều control-plane (cloud tenancy source of truth) -> identity
// (local projection), map qua platformUserId/platformCompanyId. Đây KHÔNG
// phải bản sao trùng lặp của cùng một khái niệm — xem
// docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md mục "control-plane vs
// identity — two-tier ownership".
const { identityUsers, identityWorkspaces, identityWorkspaceMembers } = schema;

export interface SyncFromPlatformParams {
  platform_access_token?: string;
  platformAccessToken?: string;
  company_id?: string | number;
  companyId?: string | number;
}

export interface SyncFromPlatformResult {
  access_token: string;
  token_type: string;
}

export async function syncFromPlatformService(params: SyncFromPlatformParams): Promise<SyncFromPlatformResult> {
  const token = params.platform_access_token || params.platformAccessToken;
  const compId = params.company_id || params.companyId;

  if (!token || !compId) {
    throw APIError.invalidArgument("vui lòng cung cấp platform_access_token và company_id");
  }

  const member = await validatePlatformMembership({
    platformToken: token,
    companyId: String(compId),
  });

  const localUserId = await db.transaction(async (tx) => {
    // 1. Tim hoac tao local user tuong ung voi platform user nay
    let [localUser] = await tx
      .select({ id: identityUsers.id, email: identityUsers.email })
      .from(identityUsers)
      .where(eq(identityUsers.platformUserId, member.userId))
      .limit(1);

    if (!localUser && member.email) {
      [localUser] = await tx
        .select({ id: identityUsers.id, email: identityUsers.email })
        .from(identityUsers)
        .where(eq(sql`LOWER(${identityUsers.email})`, member.email.toLowerCase()))
        .limit(1);
    }

    let userId: bigint;

    if (!localUser) {
      const [created] = await tx
        .insert(identityUsers)
        .values({
          email: member.email || null,
          phone: member.phone || null,
          displayName: member.displayName || null,
          platformUserId: member.userId,
          role: member.roleId,
        })
        .returning({ id: identityUsers.id });

      if (!created) throw APIError.internal("failed to create local user");
      userId = created.id;
    } else {
      userId = localUser.id;
      await tx
        .update(identityUsers)
        .set({
          platformUserId: member.userId,
          role: member.roleId,
          displayName: member.displayName || undefined,
        })
        .where(eq(identityUsers.id, userId));
    }

    // 2. Tim hoac tao workspace local cho company nay
    const [workspace] = await tx
      .select({ id: identityWorkspaces.id })
      .from(identityWorkspaces)
      .where(eq(identityWorkspaces.platformCompanyId, member.companyId))
      .limit(1);

    let isNewWorkspace = false;
    let workspaceId: bigint;

    if (!workspace) {
      isNewWorkspace = true;
      const [createdWorkspace] = await tx
        .insert(identityWorkspaces)
        .values({
          name: member.companyName,
          platformCompanyId: member.companyId,
        })
        .returning({ id: identityWorkspaces.id });

      if (!createdWorkspace) throw APIError.internal("failed to create workspace");
      workspaceId = createdWorkspace.id;
    } else {
      workspaceId = workspace.id;
    }

    // 3. Gan membership trong workspace
    const [existingMember] = await tx
      .select({ id: identityWorkspaceMembers.id })
      .from(identityWorkspaceMembers)
      .where(
        and(
          eq(identityWorkspaceMembers.workspaceId, workspaceId),
          eq(identityWorkspaceMembers.userId, userId)
        )
      )
      .limit(1);

    if (!existingMember) {
      await tx.insert(identityWorkspaceMembers).values({
        workspaceId,
        userId,
        role: isNewWorkspace ? "admin" : "member",
      });
    }

    return userId;
  });

  const localAccessToken = signAccessToken(localUserId.toString());
  return {
    access_token: localAccessToken,
    token_type: "bearer",
  };
}
