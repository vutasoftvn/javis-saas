import { APIError } from "encore.dev/api";
import { eq, sql } from "drizzle-orm";
import { db, schema } from "../models/db";
import { signAccessToken } from "./token.service";
import {
  listPlatformWorkspaceMemberships,
  validatePlatformWorkspaceMembership,
  markPlatformWorkspaceSynced,
  verifyPlatformToken,
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

export interface SyncUserPayload {
  id?: string;
  email?: string | null;
  phone?: string | null;
  full_name?: string | null;
  displayName?: string | null;
  role_id?: string | null;
}

export interface SyncWorkspacePayload {
  workspace_id?: string;
  workspaceId?: string;
  workspace_name?: string;
  workspaceName?: string;
  name?: string;
  role_id?: string;
  role?: string;
  membership_id?: string;
  membershipId?: string;
  status?: string;
}

export interface SyncFromPlatformParams {
  platform_access_token?: string;
  platformAccessToken?: string;
  user?: SyncUserPayload;
  workspaces?: SyncWorkspacePayload[];
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

  // Xác thực chữ ký token JWT từ Control Plane
  const decoded = verifyPlatformToken(token);
  const platformUserId = decoded.sub;

  let workspaceMemberships: PlatformWorkspaceMembership[];
  let isFastPath = false;

  // FAST-PATH: Nếu client truyền sẵn workspaces & user từ response của auth,
  // upsert trực tiếp vào database local trong 1ms mà không cần round-trip HTTP.
  if (params.workspaces && params.workspaces.length > 0) {
    isFastPath = true;
    workspaceMemberships = params.workspaces.map((w) => {
      const wsId = (w.workspace_id || w.workspaceId || "").toString();
      const wsName = w.workspace_name || w.workspaceName || w.name || "Workspace";
      const wsRole = w.role_id || w.role || "member";
      const memId = (w.membership_id || w.membershipId || `m-${platformUserId}-${wsId}`).toString();
      return {
        platformWorkspaceId: wsId,
        workspaceName: wsName,
        userId: platformUserId,
        email: params.user?.email || null,
        displayName: params.user?.full_name || params.user?.displayName || null,
        role: wsRole,
        membershipId: memId,
        membershipUpdatedAt: new Date().toISOString(),
      };
    });
  } else {
    // FALLBACK: Gọi control-plane RPC nếu client không truyền sẵn payload
    try {
      workspaceMemberships = (await listPlatformWorkspaceMemberships({ platformToken: token })) || [];
    } catch (err) {
      if (err instanceof APIError) throw err;
      throw APIError.unavailable(
        "không kết nối được control-plane để đồng bộ workspace — vui lòng thử lại"
      );
    }
  }

  if (workspaceMemberships && workspaceMemberships.length > 0) {
    const localUserId = await db.transaction(async (tx) => {
      let memberInfo = {
        userId: platformUserId,
        email: params.user?.email || null,
        displayName: params.user?.full_name || params.user?.displayName || null,
      };

      if (!isFastPath) {
        const firstMembership = workspaceMemberships[0];
        const member = await validatePlatformWorkspaceMembership({
          platformToken: token,
          platformWorkspaceId: firstMembership.platformWorkspaceId,
        });
        memberInfo = {
          userId: member.userId,
          email: member.email,
          displayName: member.displayName,
        };
      }

      let [localUser] = await tx
        .select({ id: identityUserProjections.id })
        .from(identityUserProjections)
        .where(eq(identityUserProjections.platformUserId, memberInfo.userId))
        .limit(1);

      if (!localUser && memberInfo.email) {
        [localUser] = await tx
          .select({ id: identityUserProjections.id })
          .from(identityUserProjections)
          .where(eq(sql`LOWER(${identityUserProjections.email})`, memberInfo.email.toLowerCase()))
          .limit(1);
      }

      let userId: bigint;
      if (localUser) {
        userId = localUser.id;
        await tx
          .update(identityUserProjections)
          .set({
            platformUserId: memberInfo.userId,
            displayName: memberInfo.displayName || undefined,
            updatedAt: new Date(),
          })
          .where(eq(identityUserProjections.id, userId));
      } else {
        const [upsertedUser] = await tx
          .insert(identityUserProjections)
          .values({
            id: generateSnowflake(),
            email: memberInfo.email || null,
            displayName: memberInfo.displayName || null,
            platformUserId: memberInfo.userId,
          })
          .onConflictDoUpdate({
            target: identityUserProjections.platformUserId,
            set: {
              displayName: memberInfo.displayName || undefined,
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
            lifecycleStage: "W0_IDEA",
            stageEnteredAt: new Date(),
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

    if (!isFastPath) {
      for (const wm of workspaceMemberships) {
        await markPlatformWorkspaceSynced({ platformWorkspaceId: wm.platformWorkspaceId, platformToken: token }).catch(() => {});
      }
    } else {
      // Async non-blocking mark synced in background
      Promise.all(
        workspaceMemberships.map((wm) =>
          markPlatformWorkspaceSynced({ platformWorkspaceId: wm.platformWorkspaceId, platformToken: token }).catch(() => {})
        )
      ).catch(() => {});
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

  // M2 §5 — bỏ hoàn toàn nhánh legacy company-membership. Company aggregate không
  // còn là tenant; mọi workspace đến từ Venture Workspace (control-plane provisioning).
  // Zero venture workspace ⇒ user chưa có workspace nào (không fallback company).
  throw APIError.failedPrecondition(
    "user chưa thuộc workspace nào — tạo workspace qua control-plane trước"
  );
}
