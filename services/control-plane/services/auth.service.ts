import { APIError } from "encore.dev/api";
import { getAuthData } from "~encore/auth";
import { eq, or, sql, and, ne } from "drizzle-orm";
import { db, schema } from "../models/db";
import { hashPassword, verifyPassword } from "./password.service";
import { signPlatformToken, verifyPlatformToken } from "./token.service";
import { generateSnowflakeStr } from "./snowflake.service";

const { users, profiles, companies, companyRoles } = schema;

export interface SessionParams {
  username?: string;
  email?: string;
  password?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  company_id?: string;
}

export interface RegisterParams {
  email: string;
  password: string;
  full_name?: string;
  phone?: string;
  company_name?: string;
  join_company_id?: number | string;
}

export interface PlatformUserProfile {
  id: string;
  email: string | null;
  phone: string | null;
  full_name: string | null;
  avatar_url: string | null;
  is_platform_admin: boolean;
  platform_role_id: string | null;
}

export interface UpdateMeParams {
  phone?: string;
  full_name?: string;
  avatar_url?: string;
}

export function extractUserId(auth?: string): string {
  const authData = getAuthData();
  if (authData?.userID) {
    return authData.userID;
  }
  if (!auth || !auth.startsWith("Bearer ")) {
    throw APIError.unauthenticated("missing or invalid authorization header");
  }
  const token = auth.slice("Bearer ".length);
  try {
    const payload = verifyPlatformToken(token);
    return payload.sub;
  } catch {
    throw APIError.unauthenticated("invalid or expired platform token");
  }
}

function slugify(name: string, userId: string): string {
  const base = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "company";
  return `${base}-${userId}`;
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

  return {
    access_token: signPlatformToken(user.id.toString()),
    token_type: "bearer",
  };
}

export async function registerPlatformUser(params: RegisterParams): Promise<TokenResponse> {
  const email = params.email.trim().toLowerCase();
  if (!email || !email.includes("@")) {
    throw APIError.invalidArgument("email không hợp lệ");
  }
  if (!params.password || params.password.length < 6) {
    throw APIError.invalidArgument("mật khẩu phải có ít nhất 6 ký tự");
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
  let companyId: string | undefined = undefined;

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
      userId: newUser.id,
      fullName: params.full_name || null,
    });

    if (params.join_company_id) {
      const joinId = BigInt(params.join_company_id.toString());
      const [comp] = await tx
        .select({ id: companies.id })
        .from(companies)
        .where(and(eq(companies.id, joinId), eq(companies.status, "active")))
        .limit(1);

      if (!comp) {
        throw APIError.notFound("company muốn tham gia không tồn tại");
      }

      const memberRoleId = BigInt(generateSnowflakeStr());
      await tx.insert(companyRoles).values({
        id: memberRoleId,
        companyId: comp.id,
        userId: newUser.id,
        roleId: "user",
      });
      companyId = comp.id.toString();
    } else if (params.company_name) {
      const compName = params.company_name.trim();
      const slug = slugify(compName, newUser.id.toString());
      const newCompId = BigInt(generateSnowflakeStr());

      const [comp] = await tx
        .insert(companies)
        .values({
          id: newCompId,
          name: compName,
          slug,
          createdBy: newUser.id,
        })
        .returning({ id: companies.id });

      const founderRoleId = BigInt(generateSnowflakeStr());
      await tx.insert(companyRoles).values({
        id: founderRoleId,
        companyId: comp.id,
        userId: newUser.id,
        roleId: "founder",
      });
      companyId = comp.id.toString();
    }
  });

  return {
    access_token: signPlatformToken(newUserId.toString()),
    token_type: "bearer",
    company_id: companyId,
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
      isPlatformAdmin: users.isPlatformAdmin,
      platformRoleId: users.platformRoleId,
    })
    .from(users)
    .leftJoin(profiles, eq(profiles.userId, users.id))
    .where(eq(users.id, userId))
    .limit(1);

  if (!userProfile) {
    throw APIError.notFound("platform user không tồn tại");
  }

  return {
    id: userProfile.id.toString(),
    email: userProfile.email,
    phone: userProfile.phone,
    full_name: userProfile.fullName,
    avatar_url: userProfile.avatarUrl,
    is_platform_admin: userProfile.isPlatformAdmin,
    platform_role_id: userProfile.platformRoleId,
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

  if (params.full_name !== undefined || params.avatar_url !== undefined) {
    await db
      .insert(profiles)
      .values({
        userId,
        fullName: params.full_name || null,
        avatarUrl: params.avatar_url || null,
        updatedAt: new Date(),
      })
      .onConflictDoUpdate({
        target: profiles.userId,
        set: {
          ...(params.full_name !== undefined ? { fullName: params.full_name } : {}),
          ...(params.avatar_url !== undefined ? { avatarUrl: params.avatar_url } : {}),
          updatedAt: new Date(),
        },
      });
  }

  return getPlatformUserProfile(userIdStr);
}
