import { api, Header, Gateway, APIError } from "encore.dev/api";
import { authHandler } from "encore.dev/auth";
import { verifyPlatformToken } from "../services/token.service";
import {
  SessionParams,
  TokenResponse,
  RegisterParams,
  PlatformUserProfile,
  UpdateMeParams,
  loginPlatformUser,
  registerPlatformUser,
  getPlatformUserProfile,
  updatePlatformUserProfile,
} from "../services/auth.service";

export { SessionParams, TokenResponse, RegisterParams, PlatformUserProfile, UpdateMeParams };

export interface AuthParams {
  authorization?: Header<"Authorization">;
}

export interface AuthData {
  userID: string;
}

// Encore's native auth mechanism (thay cho extractUserId thủ công trong từng
// handler) — xác thực Bearer token 1 lần tại Gateway, các endpoint auth:true
// tự động bị chặn nếu thiếu/sai token trước khi vào tới business logic.
export const auth = authHandler<AuthParams, AuthData>(async (params) => {
  const header = params.authorization;
  if (!header || !header.startsWith("Bearer ")) {
    throw APIError.unauthenticated("missing bearer token");
  }
  const token = header.slice("Bearer ".length);
  try {
    const decoded = verifyPlatformToken(token);
    return { userID: decoded.sub };
  } catch {
    throw APIError.unauthenticated("invalid or expired platform token");
  }
});

export const gateway = new Gateway({ authHandler: auth });

// `~encore/auth` là module ảo, chỉ được Encore sinh ra khi build/run — import
// động để không phá `encore test`/type-check khi module chưa tồn tại (cùng
// pattern với services/identity/handlers/auth.handler.ts).
export async function resolveAuthData(): Promise<AuthData> {
  let authData: AuthData | null = null;
  try {
    // @ts-ignore
    const mod = await import("~encore/auth");
    authData = mod.getAuthData();
  } catch {
    // fallback
  }
  if (!authData?.userID) {
    throw APIError.unauthenticated("missing auth data");
  }
  return authData;
}

export const loginPlatform = api(
  { method: "POST", path: "/platform/auth/sessions", expose: true, auth: false },
  async (params: SessionParams): Promise<TokenResponse> => {
    return loginPlatformUser(params);
  }
);

export const registerPlatform = api(
  { method: "POST", path: "/platform/auth/register", expose: true, auth: false },
  async (params: RegisterParams): Promise<TokenResponse> => {
    return registerPlatformUser(params);
  }
);

export async function getMe(authData: AuthData): Promise<PlatformUserProfile> {
  return getPlatformUserProfile(authData.userID);
}

export async function updateMe(authData: AuthData, params: UpdateMeParams): Promise<PlatformUserProfile> {
  return updatePlatformUserProfile(authData.userID, params);
}

export const getPlatformUserMe = api(
  { method: "GET", path: "/platform/auth/me", expose: true, auth: true },
  async (): Promise<PlatformUserProfile> => {
    return getMe(await resolveAuthData());
  }
);

export const updatePlatformUserMe = api(
  { method: "PATCH", path: "/platform/auth/me", expose: true, auth: true },
  async (params: UpdateMeParams): Promise<PlatformUserProfile> => {
    return updateMe(await resolveAuthData(), params);
  }
);
