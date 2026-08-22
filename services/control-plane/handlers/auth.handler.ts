import { api, Header } from "encore.dev/api";
import {
  SessionParams,
  TokenResponse,
  RegisterParams,
  PlatformUserProfile,
  UpdateMeParams,
  extractUserId,
  loginPlatformUser,
  registerPlatformUser,
  getPlatformUserProfile,
  updatePlatformUserProfile,
} from "../services/auth.service";

export { SessionParams, TokenResponse, RegisterParams, PlatformUserProfile, UpdateMeParams };

export interface GetPlatformUserMeParams {
  authorization?: Header<"Authorization">;
}

export interface UpdatePlatformUserMeParams extends UpdateMeParams {
  authorization?: Header<"Authorization">;
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

export const getPlatformUserMe = api(
  { method: "GET", path: "/platform/auth/me", expose: true, auth: false },
  async (params: GetPlatformUserMeParams): Promise<PlatformUserProfile> => {
    const userId = extractUserId(params.authorization);
    return getPlatformUserProfile(userId);
  }
);

export const updatePlatformUserMe = api(
  { method: "PATCH", path: "/platform/auth/me", expose: true, auth: false },
  async (params: UpdatePlatformUserMeParams): Promise<PlatformUserProfile> => {
    const userId = extractUserId(params.authorization);
    return updatePlatformUserProfile(userId, params);
  }
);
