import { APIError } from "encore.dev/api";
import { eq, sql, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { signAccessToken } from "./token.service";
import { validatePlatformMembership } from "./platform.client";
import { generateSnowflake } from "../../shared/services/snowflake.service";

// Đồng bộ một chiều control-plane (cloud tenancy source of truth) -> identity
// (local projection), map qua platformUserId/platformCompanyId. Đây KHÔNG
// phải bản sao trùng lặp của cùng một khái niệm — xem
// docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md mục "control-plane vs
// identity — two-tier ownership".
const { identityUserProjections, identityWorkspaces, identityWorkspaceMemberships } = schema;

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
    // 1. Tim hoac tao local user projection tuong ung voi platform user nay
    let [localUser] = await tx
      .select({ id: identityUserProjections.id })
      .from(identityUserProjections)
      .where(eq(identityUserProjections.platformUserId, member.userId))
      .limit(1);

    if (!localUser && member.email) {
      [localUser] = await tx
        .select({ id: identityUserProjections.id })
        .from(identityUserProjections)
        .where(eq(sql`LOWER(${identityUserProjections.email})`, member.email.toLowerCase()))
        .limit(1);
    }

    let userId: bigint;

    if (localUser) {
      userId = localUser.id;
      await tx
        .update(identityUserProjections)
        .set({
          platformUserId: member.userId,
          displayName: member.displayName || undefined,
          updatedAt: new Date(),
        })
        .where(eq(identityUserProjections.id, userId));
    } else {
      const [upsertedUser] = await tx
        .insert(identityUserProjections)
        .values({
          id: generateSnowflake(),
          email: member.email || null,
          phone: member.phone || null,
          displayName: member.displayName || null,
          platformUserId: member.userId,
        })
        .onConflictDoUpdate({
          target: identityUserProjections.platformUserId,
          set: {
            displayName: member.displayName || undefined,
            updatedAt: new Date(),
          },
        })
        .returning({ id: identityUserProjections.id });

      if (!upsertedUser) throw APIError.internal("failed to create local user projection");
      userId = upsertedUser.id;
    }

    // 2. Tim hoac tao workspace local cho company nay
    const [workspace] = await tx
      .insert(identityWorkspaces)
      .values({
        id: generateSnowflake(),
        name: member.companyName,
        platformCompanyId: member.companyId,
      })
      .onConflictDoUpdate({
        target: identityWorkspaces.platformCompanyId,
        set: {
          name: member.companyName,
          updatedAt: new Date(),
        },
      })
      .returning({ id: identityWorkspaces.id });

    if (!workspace) throw APIError.internal("failed to create workspace");
    const workspaceId = workspace.id;

    // 3. Upsert membership atomic — role/trạng thái LUÔN lấy từ platform,
    // kể cả ở lần sync thứ 2 trở đi (bug cũ: chỉ set role khi tạo mới,
    // dùng "admin"/"member" suy diễn theo isNewWorkspace thay vì role thật).
    await tx
      .insert(identityWorkspaceMemberships)
      .values({
        id: generateSnowflake(),
        workspaceId,
        userId,
        role: member.roleId,
        platformMembershipId: member.membershipId,
        sourceUpdatedAt: new Date(member.membershipUpdatedAt),
        syncedAt: new Date(),
      })
      .onConflictDoUpdate({
        target: [identityWorkspaceMemberships.workspaceId, identityWorkspaceMemberships.userId],
        set: {
          role: member.roleId,
          platformMembershipId: member.membershipId,
          sourceUpdatedAt: new Date(member.membershipUpdatedAt),
          syncedAt: new Date(),
          updatedAt: new Date(),
        },
      });

    return userId;
  });

  const localAccessToken = signAccessToken(localUserId.toString());
  return {
    access_token: localAccessToken,
    token_type: "bearer",
  };
}
