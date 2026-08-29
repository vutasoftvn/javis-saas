import { APIError } from "encore.dev/api";
import { eq, sql, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { signAccessToken } from "./token.service";
import {
  validatePlatformMembership,
  listPlatformMemberships,
  listPlatformWorkspaceMemberships,
  validatePlatformWorkspaceMembership,
  markPlatformWorkspaceSynced,
  type PlatformWorkspaceMembership,
} from "./platform.client";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { ventureProfiles } from "../../shared/db/schema/strategy";

// Đồng bộ một chiều control-plane (cloud tenancy source of truth) -> identity
// (local projection), map qua platformUserId/platformCompanyId/platformWorkspaceId.
const { identityUserProjections, identityWorkspaces, identityWorkspaceMemberships } = schema;

export interface WorkspaceSummary {
  workspaceId: string;
  name: string;
  role: string;
  status: string;
}

export interface SyncFromPlatformParams {
  platform_access_token?: string;
  platformAccessToken?: string;
}

export interface SyncFromPlatformResult {
  // M1 §1 — đây là LOCAL SESSION TOKEN (ký bằng JWT_SECRET, chỉ dùng cho local
  // business service). KHÔNG dùng token này gọi control-plane / AgentOS platform path.
  // `access_token` giữ lại làm alias tương thích ngược cho client cũ.
  local_session_token: string;
  access_token: string;
  token_type: string;
  workspaces: WorkspaceSummary[];
}

export async function syncFromPlatformService(params: SyncFromPlatformParams): Promise<SyncFromPlatformResult> {
  const token = params.platform_access_token || params.platformAccessToken;

  if (!token) {
    throw APIError.invalidArgument("vui lòng cung cấp platform_access_token");
  }

  // 1. Kiểm tra workspace memberships trước (Venture Workspace).
  // M2 §4 — KHÔNG nuốt lỗi: mảng rỗng = user chưa có venture workspace (đi tiếp),
  // exception = control-plane không phản hồi ⇒ báo sync-required rõ ràng.
  let workspaceMemberships: PlatformWorkspaceMembership[];
  try {
    workspaceMemberships = (await listPlatformWorkspaceMemberships({ platformToken: token })) || [];
  } catch (err) {
    if (err instanceof APIError) throw err;
    throw APIError.unavailable(
      "không kết nối được control-plane để đồng bộ workspace — vui lòng thử lại"
    );
  }

  if (workspaceMemberships && workspaceMemberships.length > 0) {
    const localUserId = await db.transaction(async (tx) => {
      const firstMembership = workspaceMemberships[0];
      const member = await validatePlatformWorkspaceMembership({
        platformToken: token,
        platformWorkspaceId: firstMembership.platformWorkspaceId,
      });

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

      for (const wm of workspaceMemberships) {
        // M2 §4 / C-6 — workspace ID do control-plane mint; local dùng ĐÚNG id đó,
        // KHÔNG generateSnowflake() ⇒ một workspace identity duy nhất xuyên plane.
        const workspaceSpineId = BigInt(wm.platformWorkspaceId);
        const [workspace] = await tx
          .insert(identityWorkspaces)
          .values({
            id: workspaceSpineId,
            name: wm.workspaceName,
            platformWorkspaceId: wm.platformWorkspaceId, // giữ tạm cho call site cũ; id === giá trị này
            companyStage: "S0_GENESIS",
            ventureStageEnteredAt: new Date(),
          })
          .onConflictDoUpdate({
            target: identityWorkspaces.id,
            set: {
              name: wm.workspaceName,
              platformWorkspaceId: wm.platformWorkspaceId,
              updatedAt: new Date(),
            },
          })
          .returning({ id: identityWorkspaces.id });

        if (!workspace) throw APIError.internal("failed to create workspace");
        const workspaceId = workspace.id;

        await tx
          .insert(identityWorkspaceMemberships)
          .values({
            id: generateSnowflake(),
            workspaceId,
            userId,
            role: wm.role,
            platformMembershipId: wm.membershipId,
            sourceUpdatedAt: new Date(wm.membershipUpdatedAt),
            syncedAt: new Date(),
          })
          .onConflictDoUpdate({
            target: [identityWorkspaceMemberships.workspaceId, identityWorkspaceMemberships.userId],
            set: {
              role: wm.role,
              platformMembershipId: wm.membershipId,
              sourceUpdatedAt: new Date(wm.membershipUpdatedAt),
              syncedAt: new Date(),
              updatedAt: new Date(),
            },
          });

        // Bootstrap venture profile
        await tx
          .insert(ventureProfiles)
          .values({
            id: generateSnowflake(),
            workspaceId,
            stageEnteredAt: new Date(),
          })
          .onConflictDoNothing();
      }

      return userId;
    });

    for (const wm of workspaceMemberships) {
      await markPlatformWorkspaceSynced({ platformWorkspaceId: wm.platformWorkspaceId });
    }

    const workspaces = await db
      .select({
        id: identityWorkspaces.id,
        name: identityWorkspaces.name,
        role: identityWorkspaceMemberships.role,
      })
      .from(identityWorkspaces)
      .innerJoin(
        identityWorkspaceMemberships,
        eq(identityWorkspaceMemberships.workspaceId, identityWorkspaces.id)
      )
      .where(eq(identityWorkspaceMemberships.userId, localUserId));

    const localAccessToken = signAccessToken(localUserId.toString());
    return {
      local_session_token: localAccessToken,
      access_token: localAccessToken,
      token_type: "bearer",
      workspaces: workspaces.map((ws) => ({
        workspaceId: ws.id.toString(),
        name: ws.name,
        role: ws.role,
        status: "active",
      })),
    };
  }

  // Fallback: legacy company memberships
  const memberships = await listPlatformMemberships({ platformToken: token });

  if (!memberships || memberships.length === 0) {
    throw APIError.invalidArgument("user không là thành viên của workspace nào");
  }

  const localUserId = await db.transaction(async (tx) => {
    // Để lấy userId, ta cần validate ít nhất một membership để có user info.
    // Chọn membership đầu tiên để lấy user metadata (email, displayName, etc.)
    const firstMembership = memberships[0];
    const member = await validatePlatformMembership({
      platformToken: token,
      companyId: firstMembership.companyId,
    });

    // 1. Tìm hoặc tạo local user projection tương ứng với platform user này
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

    // 2. Upsert mỗi workspace cho mỗi platform company membership
    for (const membership of memberships) {
      const memberDetail = membership.companyId === firstMembership.companyId
        ? member
        : await validatePlatformMembership({
            platformToken: token,
            companyId: membership.companyId,
          });

      const [workspace] = await tx
        .insert(identityWorkspaces)
        .values({
          id: generateSnowflake(),
          name: memberDetail.companyName,
          platformCompanyId: memberDetail.companyId,
        })
        .onConflictDoUpdate({
          target: identityWorkspaces.platformCompanyId,
          set: {
            name: memberDetail.companyName,
            updatedAt: new Date(),
          },
        })
        .returning({ id: identityWorkspaces.id });

      if (!workspace) throw APIError.internal("failed to create workspace");
      const workspaceId = workspace.id;

      // 3. Upsert membership atomic — role/trạng thái LUÔN lấy từ platform,
      // kể cả ở lần sync thứ 2 trở đi
      await tx
        .insert(identityWorkspaceMemberships)
        .values({
          id: generateSnowflake(),
          workspaceId,
          userId,
          role: memberDetail.roleId,
          platformMembershipId: memberDetail.membershipId,
          sourceUpdatedAt: new Date(memberDetail.membershipUpdatedAt),
          syncedAt: new Date(),
        })
        .onConflictDoUpdate({
          target: [identityWorkspaceMemberships.workspaceId, identityWorkspaceMemberships.userId],
          set: {
            role: memberDetail.roleId,
            platformMembershipId: memberDetail.membershipId,
            sourceUpdatedAt: new Date(memberDetail.membershipUpdatedAt),
            syncedAt: new Date(),
            updatedAt: new Date(),
          },
        });
    }

    return userId;
  });

  // Lấy danh sách workspace của user để trả về
  const workspaces = await db
    .select({
      id: identityWorkspaces.id,
      name: identityWorkspaces.name,
      role: identityWorkspaceMemberships.role,
    })
    .from(identityWorkspaces)
    .innerJoin(
      identityWorkspaceMemberships,
      eq(identityWorkspaceMemberships.workspaceId, identityWorkspaces.id)
    )
    .where(eq(identityWorkspaceMemberships.userId, localUserId));

  const localAccessToken = signAccessToken(localUserId.toString());
  return {
    local_session_token: localAccessToken,
    access_token: localAccessToken,
    token_type: "bearer",
    workspaces: workspaces.map((ws) => ({
      workspaceId: ws.id.toString(),
      name: ws.name,
      role: ws.role,
      status: "active",
    })),
  };
}
