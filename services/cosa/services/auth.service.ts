import { APIError } from "encore.dev/api";
import { eq, and, ne } from "drizzle-orm";
import { db, schema } from "../models/db";

const { users, profiles } = schema;

export type SupportedLocale = "vi-VN" | "en-US";
export const SUPPORTED_LOCALES: readonly SupportedLocale[] = ["vi-VN", "en-US"] as const;

export function parseSupportedLocale(value: string): SupportedLocale {
  if (value === "vi-VN" || value === "en-US") return value;
  throw APIError.invalidArgument("unsupported preferred_locale");
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
  preferred_locale: SupportedLocale;
}

export interface UpdateMeParams {
  preferred_locale?: SupportedLocale;
  preferredLocale?: SupportedLocale;
  phone?: string;
  full_name?: string;
  display_name?: string;
  displayName?: string;
  avatar_url?: string;
  headline?: string;
  bio?: string;
}

/**
 * Spec 2026-09-25 §8 — COSA chỉ sở hữu preference (locale/headline/bio).
 * Phone/email/tên hiển thị/avatar thuộc Core; route preference từ chối các
 * trường đó thay vì âm thầm ghi vào projection.
 */
export interface UpdateCosaPreferenceParams {
  preferredLocale?: SupportedLocale;
  headline?: string;
  bio?: string;
  // Khai báo chỉ để phát hiện và từ chối — không bao giờ được ghi.
  phone?: string;
  email?: string;
  display_name?: string;
  displayName?: string;
  full_name?: string;
  fullName?: string;
  avatar_url?: string;
  avatarUrl?: string;
}

const CORE_OWNED_PROFILE_FIELDS = [
  "phone",
  "email",
  "display_name",
  "displayName",
  "full_name",
  "fullName",
  "avatar_url",
  "avatarUrl",
] as const;

/** Từ chối mọi trường liên hệ thuộc Core trong một lệnh tự cập nhật hồ sơ ở COSA. */
export function assertNoCoreOwnedProfileFields(params: Partial<Record<(typeof CORE_OWNED_PROFILE_FIELDS)[number], unknown>>): void {
  const coreOwned = CORE_OWNED_PROFILE_FIELDS.filter((field) => params[field] !== undefined);
  if (coreOwned.length > 0) {
    throw APIError.invalidArgument(
      `${coreOwned.join(", ")} is owned by core; update it through the core profile API`
    );
  }
}

/**
 * `PATCH /platform/auth/me` chỉ còn ghi preference thuộc COSA; phone/tên
 * hiển thị/avatar đi thẳng tới API profile của Core (spec 2026-09-25 §8).
 */
export async function updateOwnPlatformProfile(
  userIdStr: string,
  params: UpdateMeParams
): Promise<PlatformUserProfile> {
  assertNoCoreOwnedProfileFields(params);
  return updatePlatformUserProfile(userIdStr, {
    preferred_locale: params.preferred_locale,
    preferredLocale: params.preferredLocale,
    headline: params.headline,
    bio: params.bio,
  });
}

export async function updateCosaPreferences(
  userIdStr: string,
  params: UpdateCosaPreferenceParams
): Promise<PlatformUserProfile> {
  assertNoCoreOwnedProfileFields(params);
  if (params.headline !== undefined && params.headline.length > 200) {
    throw APIError.invalidArgument("headline must be at most 200 characters");
  }
  if (params.bio !== undefined && params.bio.length > 2000) {
    throw APIError.invalidArgument("bio must be at most 2000 characters");
  }
  return updatePlatformUserProfile(userIdStr, {
    preferredLocale: params.preferredLocale,
    headline: params.headline,
    bio: params.bio,
  });
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
      preferredLocale: profiles.preferredLocale,
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
    preferred_locale: (userProfile.preferredLocale as SupportedLocale) || "vi-VN",
  };
}

export async function updatePlatformUserProfile(
  userIdStr: string,
  params: UpdateMeParams
): Promise<PlatformUserProfile> {
  const userId = BigInt(userIdStr);

  const preferredLocale = params.preferred_locale ?? params.preferredLocale;
  if (preferredLocale !== undefined) {
    parseSupportedLocale(preferredLocale);
  }

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

  const fullName = params.full_name ?? params.display_name ?? params.displayName;
  if (
    fullName !== undefined ||
    params.avatar_url !== undefined ||
    params.headline !== undefined ||
    params.bio !== undefined ||
    preferredLocale !== undefined
  ) {
    await db
      .insert(profiles)
      .values({
        id: userId,
        fullName: fullName || null,
        avatarUrl: params.avatar_url || null,
        headline: params.headline || null,
        bio: params.bio || null,
        preferredLocale: preferredLocale || "vi-VN",
        updatedAt: new Date(),
      })
      .onConflictDoUpdate({
        target: profiles.id,
        set: {
          ...(fullName !== undefined ? { fullName } : {}),
          ...(params.avatar_url !== undefined ? { avatarUrl: params.avatar_url } : {}),
          ...(params.headline !== undefined ? { headline: params.headline } : {}),
          ...(params.bio !== undefined ? { bio: params.bio } : {}),
          ...(preferredLocale !== undefined ? { preferredLocale } : {}),
          updatedAt: new Date(),
        },
      });
  }

  return getPlatformUserProfile(userIdStr);
}

