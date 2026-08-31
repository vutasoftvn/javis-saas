import { APIError } from "encore.dev/api";
import { eq, or, sql, and, ne } from "drizzle-orm";
import { db, schema } from "../models/db";
import { hashPassword, verifyPassword } from "./password.service";
import { signPlatformToken } from "./token.service";
import { generateSnowflakeStr } from "./snowflake.service";
import { provisionVentureWorkspace } from "./venture-workspace.service";

const {
  users,
  profiles,
  platformWorkspaces,
  platformWorkspaceMemberships,
  workspaceLicenses,
  workspaceEntitlements,
  platformWorkspaceSyncLog,
  plans,
} = schema;

export interface SessionParams {
  username?: string;
  email?: string;
  password?: string;
}

export interface UserPayload {
  id: string;
  email: string | null;
  phone: string | null;
  full_name: string | null;
  role_id: string | null;
}

export interface WorkspaceSummaryPayload {
  workspace_id: string;
  workspace_name: string;
  role_id: string;
  membership_id?: string;
  status: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user?: UserPayload;
  workspaces?: WorkspaceSummaryPayload[];
  platform_workspace_id?: string;
  workspace_provision_status?: "pending" | "synced";
}

export interface RegisterParams {
  email: string;
  password: string;
  full_name?: string;
  phone?: string;
  workspace_name?: string;
  company_name?: string; // backwards compatibility alias mapped to workspace_name
  client_workspace_creation_id?: string;
}

export interface PlatformUserProfile {
  id: string;
  email: string | null;
  phone: string | null;
  full_name: string | null;
  avatar_url: string | null;
  role_id: string | null;
  headline?: string | null;
  bio?: string | null;
  is_platform_admin?: boolean;
  platform_role_id?: string | null;
}

export interface UpdateMeParams {
  phone?: string;
  full_name?: string;
  avatar_url?: string;
  headline?: string;
  bio?: string;
}

export async function loginPlatformUser(params: SessionParams): Promise<TokenResponse> {
  const identifier = (params.username || params.email || "").trim().toLowerCase();
  const password = params.password || "";

  if (!identifier || !password) {
    throw APIError.invalidArgument("vui lòng nhập tài khoản và mật khẩu");
  }

  const [user] = await db
    .select({
      id: users.id,
      email: users.email,
      phone: users.phone,
      hashedPassword: users.hashedPassword,
    })
    .from(users)
    .where(or(eq(sql`LOWER(${users.email})`, identifier), eq(users.phone, identifier)))
    .limit(1);

  if (!user || !user.hashedPassword) {
    throw APIError.unauthenticated("email hoặc mật khẩu không chính xác");
  }

  const isValid = await verifyPassword(password, user.hashedPassword);
  if (!isValid) {
    throw APIError.unauthenticated("email hoặc mật khẩu không chính xác");
  }

  await db
    .update(users)
    .set({ lastLoginAt: new Date() })
    .where(eq(users.id, user.id));

  const [profile] = await db
    .select({
      fullName: profiles.fullName,
      roleId: profiles.roleId,
    })
    .from(profiles)
    .where(eq(profiles.id, user.id))
    .limit(1);

  const memberships = await db
    .select({
      membershipId: schema.workspaceMemberships.id,
      workspaceId: schema.workspaceMemberships.workspaceId,
      roleId: schema.workspaceMemberships.roleId,
      workspaceName: schema.workspaces.workspaceName,
      status: schema.workspaces.status,
    })
    .from(schema.workspaceMemberships)
    .innerJoin(schema.workspaces, eq(schema.workspaces.id, schema.workspaceMemberships.workspaceId))
    .where(and(eq(schema.workspaceMemberships.userId, user.id), eq(schema.workspaces.status, "active")));

  return {
    access_token: signPlatformToken(user.id.toString()),
    token_type: "bearer",
    user: {
      id: user.id.toString(),
      email: user.email,
      phone: user.phone,
      full_name: profile?.fullName || null,
      role_id: profile?.roleId || "member",
    },
    workspaces: memberships.map((m) => ({
      workspace_id: m.workspaceId.toString(),
      workspace_name: m.workspaceName,
      role_id: m.roleId,
      membership_id: m.membershipId.toString(),
      status: m.status,
    })),
  };
}

export async function registerPlatformUser(params: RegisterParams): Promise<TokenResponse> {
  const email = params.email.trim().toLowerCase();
  if (!email || !email.includes("@")) {
    throw APIError.invalidArgument("email không hợp lệ");
  }
  if (!params.password || params.password.length < 12 || params.password.length > 128) {
    throw APIError.invalidArgument("mật khẩu phải có từ 12 đến 128 ký tự");
  }

  const [existing] = await db
    .select({ id: users.id })
    .from(users)
    .where(eq(sql`LOWER(${users.email})`, email))
    .limit(1);

  if (existing) {
    throw APIError.alreadyExists("email đã được đăng ký");
  }

  const passwordHash = await hashPassword(params.password);
  const newUserId = BigInt(generateSnowflakeStr());

  const explicitWsName = params.workspace_name?.trim() || params.company_name?.trim();
  const initialRole = explicitWsName ? "founder" : "member";

  await db.transaction(async (tx) => {
    const [newUser] = await tx
      .insert(users)
      .values({
        id: newUserId,
        email,
        phone: params.phone || null,
        hashedPassword: passwordHash,
      })
      .returning({ id: users.id });

    await tx.insert(profiles).values({
      id: newUser.id,
      roleId: initialRole,
      fullName: params.full_name || null,
    });
  });

  let platformWorkspaceId: string | undefined;
  let provWorkspaces: WorkspaceSummaryPayload[] | undefined;
  if (explicitWsName) {
    const cid = params.client_workspace_creation_id || `auto-${newUserId.toString()}`;
    const prov = await provisionVentureWorkspace({
      ownerUserId: newUserId,
      workspaceName: explicitWsName,
      clientCreationId: cid,
    });
    platformWorkspaceId = prov.platformWorkspaceId;
    provWorkspaces = [
      {
        workspace_id: prov.platformWorkspaceId,
        workspace_name: explicitWsName,
        role_id: "founder",
        status: "active",
      },
    ];
  }

  return {
    access_token: signPlatformToken(newUserId.toString()),
    token_type: "bearer",
    user: {
      id: newUserId.toString(),
      email,
      phone: params.phone || null,
      full_name: params.full_name || null,
      role_id: initialRole,
    },
    workspaces: provWorkspaces,
    platform_workspace_id: platformWorkspaceId,
    workspace_provision_status: platformWorkspaceId ? "pending" : undefined,
  };
}

export async function getPlatformUserProfile(userIdStr: string): Promise<PlatformUserProfile> {
  const userId = BigInt(userIdStr);
  const [userProfile] = await db
    .select({
      id: users.id,
      email: users.email,
      phone: users.phone,
      fullName: profiles.fullName,
      avatarUrl: profiles.avatarUrl,
      roleId: profiles.roleId,
      headline: profiles.headline,
      bio: profiles.bio,
    })
    .from(users)
    .leftJoin(profiles, eq(profiles.id, users.id))
    .where(eq(users.id, userId))
    .limit(1);

  if (!userProfile) {
    throw APIError.notFound("platform user không tồn tại");
  }

  const isPlatformAdmin = userProfile.roleId === "superadmin" || userProfile.roleId === "admin";

  return {
    id: userProfile.id.toString(),
    email: userProfile.email,
    phone: userProfile.phone,
    full_name: userProfile.fullName,
    avatar_url: userProfile.avatarUrl,
    role_id: userProfile.roleId,
    headline: userProfile.headline,
    bio: userProfile.bio,
    is_platform_admin: isPlatformAdmin,
    platform_role_id: userProfile.roleId,
  };
}

export async function updatePlatformUserProfile(
  userIdStr: string,
  params: UpdateMeParams
): Promise<PlatformUserProfile> {
  const userId = BigInt(userIdStr);

  if (params.phone !== undefined) {
    if (params.phone) {
      const [conflict] = await db
        .select({ id: users.id })
        .from(users)
        .where(and(eq(users.phone, params.phone), ne(users.id, userId)))
        .limit(1);

      if (conflict) {
        throw APIError.alreadyExists("số điện thoại đã được đăng ký");
      }
    }
    await db
      .update(users)
      .set({ phone: params.phone || null, updatedAt: new Date() })
      .where(eq(users.id, userId));
  }

  if (
    params.full_name !== undefined ||
    params.avatar_url !== undefined ||
    params.headline !== undefined ||
    params.bio !== undefined
  ) {
    await db
      .insert(profiles)
      .values({
        id: userId,
        fullName: params.full_name || null,
        avatarUrl: params.avatar_url || null,
        headline: params.headline || null,
        bio: params.bio || null,
        updatedAt: new Date(),
      })
      .onConflictDoUpdate({
        target: profiles.id,
        set: {
          ...(params.full_name !== undefined ? { fullName: params.full_name } : {}),
          ...(params.avatar_url !== undefined ? { avatarUrl: params.avatar_url } : {}),
          ...(params.headline !== undefined ? { headline: params.headline } : {}),
          ...(params.bio !== undefined ? { bio: params.bio } : {}),
          updatedAt: new Date(),
        },
      });
  }

  return getPlatformUserProfile(userIdStr);
}

