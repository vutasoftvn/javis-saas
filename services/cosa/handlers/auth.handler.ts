import { api, Header, Gateway, APIError } from "encore.dev/api";
import { authHandler } from "encore.dev/auth";
import { resolveCallerIdentity } from "../services/core-access.service";
import { resolveCallerAuthorizedForWorkspace } from "../services/workspace-connector.service";
import {
  PlatformUserProfile,
  UpdateMeParams,
  SupportedLocale,
  getPlatformUserProfile,
  updateOwnPlatformProfile,
  updateCosaPreferences,
  UpdateCosaPreferenceParams,
} from "../services/auth.service";

export { PlatformUserProfile, UpdateMeParams, SupportedLocale };

export interface AuthParams {
  authorization?: Header<"Authorization">;
}

export interface AuthData {
  userID: string;
  /** Access token OIDC của core, để chuyển tiếp sang core (tạo organization, nhận lời mời...). */
  accessToken: string;
}

// Danh tính do backend/core quản lý: chỉ nhận access token OIDC (chuỗi opaque, xem core-access.service).
export async function resolveBearerAuthData(header: string | undefined): Promise<AuthData> {
  if (!header || !header.startsWith("Bearer ")) {
    throw APIError.unauthenticated("missing bearer token");
  }
  const caller = await resolveCallerIdentity(header.slice("Bearer ".length));
  return { userID: caller.userId, accessToken: caller.accessToken };
}

// Encore's native auth mechanism (thay cho extractUserId thủ công trong từng
// handler) — xác thực Bearer token 1 lần tại Gateway, các endpoint auth:true
// tự động bị chặn nếu thiếu/sai token trước khi vào tới business logic.
export const auth = authHandler<AuthParams, AuthData>(async (params) => {
  return resolveBearerAuthData(params.authorization);
});

export const gateway = new Gateway({ authHandler: auth });

// `~encore/auth` là module ảo, chỉ được Encore sinh ra khi build/run — import
// động để không phá `encore test`/type-check khi module chưa tồn tại (cùng
// pattern với services/identity/handlers/auth.handler.ts).
export async function resolveAuthData(): Promise<AuthData> {
  let authData: AuthData | null = null;
  try {
    const mod = await import("~encore/auth");
    authData = mod.getAuthData<AuthData>();
  } catch {
    // fallback
  }
  if (!authData?.userID) {
    throw APIError.unauthenticated("missing auth data");
  }
  return authData;
}

export async function getMe(authData: AuthData): Promise<PlatformUserProfile> {
  return getPlatformUserProfile(authData.userID);
}

export async function updateMe(authData: AuthData, params: UpdateMeParams): Promise<PlatformUserProfile> {
  return updateOwnPlatformProfile(authData.userID, params);
}

export const getPlatformUserMe = api(
  { method: "GET", path: "/platform/auth/me", expose: true, auth: true },
  async (): Promise<PlatformUserProfile> => {
    return getMe(await resolveAuthData());
  }
);

export const updatePlatformUserMe = api(
  { method: "PATCH", path: "/platform/auth/me", expose: true, auth: true },
  async (params: UpdateMeParams & { role_id?: unknown }): Promise<PlatformUserProfile> => {
    if (params.role_id !== undefined) throw APIError.invalidArgument("role_id cannot be changed by profile update");
    return updateMe(await resolveAuthData(), params);
  }
);

// Spec 2026-09-25 §8 — route chỉ cho preference thuộc COSA.
export const updateMyCosaPreferences = api(
  { method: "PATCH", path: "/platform/preferences/me", expose: true, auth: true },
  async (params: UpdateCosaPreferenceParams): Promise<PlatformUserProfile> => {
    const authData = await resolveAuthData();
    return updateCosaPreferences(authData.userID, params);
  }
);

export interface GetLocaleSnapshotParams {
  organizationId: string;
  authorization?: Header<"Authorization">;
}

export interface LocaleSnapshot {
  workspace_id: string;
  preferred_locale: SupportedLocale;
}

export const getPlatformUserLocaleSnapshot = api(
  { method: "GET", path: "/platform/auth/me/locale-snapshot", expose: true, auth: false },
  async (params: GetLocaleSnapshotParams): Promise<LocaleSnapshot> => {
    const caller = await resolveCallerAuthorizedForWorkspace(params.authorization, params.organizationId);
    const profile = await getPlatformUserProfile(caller.sub);
    return {
      workspace_id: params.organizationId,
      preferred_locale: profile.preferred_locale,
    };
  }
);

export const getLocaleSnapshotForWorkspace = getPlatformUserLocaleSnapshot;

