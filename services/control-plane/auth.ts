import { api, APIError, Header } from "encore.dev/api";
import { controlPlaneDB } from "./db";
import { hashPassword, verifyPassword } from "./password";
import { signPlatformToken, verifyPlatformToken } from "./token";

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

interface AuthHeader {
  authorization?: Header<"Authorization">;
}

function extractUserId(auth?: string): string {
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

function slugify(name: string, userId: number | string): string {
  const base = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "company";
  return `${base}-${userId}`;
}

export const loginPlatform = api(
  { method: "POST", path: "/platform/auth/sessions", expose: true },
  async (params: SessionParams): Promise<TokenResponse> => {
    const identifier = (params.username || params.email || "").trim().toLowerCase();
    const password = params.password || "";

    if (!identifier || !password) {
      throw APIError.invalidArgument("vui lòng nhập tài khoản và mật khẩu");
    }

    const row = await controlPlaneDB.queryRow<{ id: number; hashed_password: string }>`
      SELECT id, hashed_password FROM control_plane.users
      WHERE LOWER(email) = ${identifier} OR phone = ${identifier}
    `;

    if (!row || !row.hashed_password) {
      throw APIError.unauthenticated("email hoặc mật khẩu không chính xác");
    }

    const isValid = await verifyPassword(password, row.hashed_password);
    if (!isValid) {
      throw APIError.unauthenticated("email hoặc mật khẩu không chính xác");
    }

    await controlPlaneDB.exec`
      UPDATE control_plane.users SET last_login_at = now() WHERE id = ${row.id}
    `;

    return {
      access_token: signPlatformToken(String(row.id)),
      token_type: "bearer",
    };
  }
);

export const registerPlatform = api(
  { method: "POST", path: "/platform/auth/register", expose: true },
  async (params: RegisterParams): Promise<TokenResponse> => {
    const email = params.email.trim().toLowerCase();
    if (!email || !email.includes("@")) {
      throw APIError.invalidArgument("email không hợp lệ");
    }
    if (!params.password || params.password.length < 6) {
      throw APIError.invalidArgument("mật khẩu phải có ít nhất 6 ký tự");
    }

    const existing = await controlPlaneDB.queryRow<{ id: number }>`
      SELECT id FROM control_plane.users WHERE LOWER(email) = ${email}
    `;
    if (existing) {
      throw APIError.alreadyExists("email đã được đăng ký");
    }

    const passwordHash = await hashPassword(params.password);
    const tx = await controlPlaneDB.begin();
    try {
      const userRow = await tx.queryRow<{ id: number }>`
        INSERT INTO control_plane.users (email, phone, hashed_password)
        VALUES (${email}, ${params.phone ?? null}, ${passwordHash})
        RETURNING id
      `;
      if (!userRow) throw APIError.internal("failed to create platform user");

      await tx.exec`
        INSERT INTO control_plane.profiles (user_id, full_name)
        VALUES (${userRow.id}, ${params.full_name ?? null})
      `;

      let companyId: string | undefined = undefined;

      if (params.join_company_id) {
        const joinId = Number(params.join_company_id);
        const comp = await tx.queryRow<{ id: number }>`
          SELECT id FROM control_plane.companies WHERE id = ${joinId} AND status = 'active'
        `;
        if (!comp) {
          throw APIError.notFound("company muốn tham gia không tồn tại");
        }
        await tx.exec`
          INSERT INTO control_plane.company_roles (company_id, user_id, role_id)
          VALUES (${comp.id}, ${userRow.id}, 'user')
        `;
        companyId = String(comp.id);
      } else if (params.company_name) {
        const compName = params.company_name.trim();
        const slug = slugify(compName, userRow.id);
        const comp = await tx.queryRow<{ id: number }>`
          INSERT INTO control_plane.companies (name, slug, created_by)
          VALUES (${compName}, ${slug}, ${userRow.id})
          RETURNING id
        `;
        if (!comp) throw APIError.internal("failed to create company");

        await tx.exec`
          INSERT INTO control_plane.company_roles (company_id, user_id, role_id)
          VALUES (${comp.id}, ${userRow.id}, 'founder')
        `;
        companyId = String(comp.id);
      }

      await tx.commit();

      return {
        access_token: signPlatformToken(String(userRow.id)),
        token_type: "bearer",
        company_id: companyId,
      };
    } catch (err) {
      await tx.rollback();
      throw err;
    }
  }
);

export const getPlatformUserMe = api(
  { method: "GET", path: "/platform/auth/me", expose: true },
  async (headers: AuthHeader): Promise<PlatformUserProfile> => {
    const userId = extractUserId(headers.authorization);
    const row = await controlPlaneDB.queryRow<{
      id: number;
      email: string | null;
      phone: string | null;
      full_name: string | null;
      avatar_url: string | null;
      is_platform_admin: boolean;
      platform_role_id: string | null;
    }>`
      SELECT u.id, u.email, u.phone, p.full_name, p.avatar_url, u.is_platform_admin, u.platform_role_id
      FROM control_plane.users u
      LEFT JOIN control_plane.profiles p ON p.user_id = u.id
      WHERE u.id = ${Number(userId)}
    `;

    if (!row) {
      throw APIError.notFound("platform user không tồn tại");
    }

    return {
      id: String(row.id),
      email: row.email,
      phone: row.phone,
      full_name: row.full_name,
      avatar_url: row.avatar_url,
      is_platform_admin: row.is_platform_admin,
      platform_role_id: row.platform_role_id,
    };
  }
);

export const updatePlatformUserMe = api(
  { method: "PATCH", path: "/platform/auth/me", expose: true },
  async (params: UpdateMeParams, headers: AuthHeader): Promise<PlatformUserProfile> => {
    const userId = Number(extractUserId(headers.authorization));

    if (params.phone !== undefined) {
      if (params.phone) {
        const conflict = await controlPlaneDB.queryRow<{ id: number }>`
          SELECT id FROM control_plane.users WHERE phone = ${params.phone} AND id != ${userId}
        `;
        if (conflict) {
          throw APIError.alreadyExists("số điện thoại đã được đăng ký");
        }
      }
      await controlPlaneDB.exec`
        UPDATE control_plane.users SET phone = ${params.phone || null}, updated_at = now() WHERE id = ${userId}
      `;
    }

    if (params.full_name !== undefined || params.avatar_url !== undefined) {
      await controlPlaneDB.exec`
        INSERT INTO control_plane.profiles (user_id, full_name, avatar_url, updated_at)
        VALUES (${userId}, ${params.full_name ?? null}, ${params.avatar_url ?? null}, now())
        ON CONFLICT (user_id) DO UPDATE SET
          full_name = COALESCE(${params.full_name ?? null}, control_plane.profiles.full_name),
          avatar_url = COALESCE(${params.avatar_url ?? null}, control_plane.profiles.avatar_url),
          updated_at = now()
      `;
    }

    return getPlatformUserMe(headers);
  }
);
