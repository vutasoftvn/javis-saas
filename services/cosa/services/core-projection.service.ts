import { db, schema } from "../models/db";
import { generateSnowflakeStr } from "./snowflake.service";

const { users, profiles, workspaces, workspaceMemberships } = schema;

/**
 * Bản chiếu (projection) của user và organization từ backend/core (migration 006).
 * Core là nguồn sự thật (danh tính, mật khẩu, organization, role); COSA chỉ giữ dòng cục bộ
 * cùng id với core để các bảng vận hành (connector, policy, schedule...) có FK. Mọi request bằng
 * access token của core đều upsert lại bản chiếu này từ quyết định mới nhất của core.
 */

export interface CoreUserProjection {
  userId: string;
  email?: string | null;
  phone?: string | null;
  displayName?: string | null;
  avatarUrl?: string | null;
}

export interface CoreOrganizationProjection {
  organizationId: string;
  name: string;
  ownerUserId: string;
}

export interface ProjectCoreAccessInput {
  user: CoreUserProjection;
  organization: CoreOrganizationProjection;
  /** Role của user trong organization theo core. */
  role: string;
}

const COSA_ROLES = new Set(["founder", "co-founder", "admin", "member", "viewer"]);

/** Role của core -> role của COSA (CHECK ở cosa.organization_memberships). */
export function mapCoreRoleToCosaRole(coreRole: string): string {
  if (coreRole === "owner") return "founder";
  return COSA_ROLES.has(coreRole) ? coreRole : "member";
}

type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];

async function upsertUserAndProfile(tx: Tx, user: CoreUserProjection, now: Date): Promise<void> {
  const userId = BigInt(user.userId);
  const email = user.email ?? null;
  const phone = user.phone ?? null;
  // users_email_or_phone_required: core luôn có ít nhất một, giữ chỗ phòng thủ nếu thiếu cả hai.
  const effectiveEmail = email ?? (phone ? null : `user-${user.userId}@core.invalid`);

  await tx
    .insert(users)
    .values({ id: userId, email: effectiveEmail, phone, hashedPassword: null })
    .onConflictDoUpdate({
      target: users.id,
      set: { email: effectiveEmail, phone, updatedAt: now },
    });

  await tx
    .insert(profiles)
    .values({
      id: userId,
      fullName: user.displayName ?? null,
      avatarUrl: user.avatarUrl ?? null,
    })
    .onConflictDoUpdate({
      target: profiles.id,
      // Không đụng preferredLocale/roleId: người dùng tự chỉnh ở COSA.
      set: {
        fullName: user.displayName ?? null,
        avatarUrl: user.avatarUrl ?? null,
        updatedAt: now,
      },
    });
}

/** Chiếu riêng user (endpoint chưa gắn organization, vd tạo organization đầu tiên). */
export async function projectCoreUser(user: CoreUserProjection): Promise<void> {
  const now = new Date();
  await db.transaction(async (tx) => {
    await upsertUserAndProfile(tx, user, now);
  });
}

export async function projectCoreAccess(input: ProjectCoreAccessInput): Promise<void> {
  const userId = BigInt(input.user.userId);
  const organizationId = BigInt(input.organization.organizationId);
  const ownerId = BigInt(input.organization.ownerUserId);
  const cosaRole = mapCoreRoleToCosaRole(input.role);
  const now = new Date();

  await db.transaction(async (tx) => {
    await upsertUserAndProfile(tx, input.user, now);

    await tx
      .insert(workspaces)
      .values({ id: organizationId, workspaceName: input.organization.name, ownerId })
      .onConflictDoUpdate({
        target: workspaces.id,
        set: { workspaceName: input.organization.name, ownerId, updatedAt: now },
      });

    await tx
      .insert(workspaceMemberships)
      .values({
        id: BigInt(generateSnowflakeStr()),
        workspaceId: organizationId,
        userId,
        roleId: cosaRole,
      })
      .onConflictDoUpdate({
        target: [workspaceMemberships.workspaceId, workspaceMemberships.userId],
        set: { roleId: cosaRole, updatedAt: now },
      });
  });
}
