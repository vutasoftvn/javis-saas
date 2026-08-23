import { api, Header, Gateway, APIError } from "encore.dev/api";
import { authHandler } from "encore.dev/auth";
import { verifyAccessToken } from "../services/token.service";
import { verifyPlatformToken } from "../services/platform.client";
import {
  LoginParams,
  LoginResult,
  RegisterParams,
  RegisterResult,
  MeResponse,
  loginUser,
  registerUserService,
  getMeProfile,
} from "../services/auth.service";

export { LoginParams, LoginResult, RegisterParams, RegisterResult, MeResponse };

export interface AuthParams {
  authorization?: Header<"Authorization">;
}

export interface AuthData {
  userID: string;
}

export const auth = authHandler<AuthParams, AuthData>(async (params) => {
  const header = params.authorization;
  if (!header || !header.startsWith("Bearer ")) {
    throw APIError.unauthenticated("missing bearer token");
  }
  const token = header.slice("Bearer ".length);
  try {
    const decoded = verifyAccessToken(token);
    return { userID: decoded.sub };
  } catch {
    try {
      const pDecoded = verifyPlatformToken(token);
      return { userID: pDecoded.sub };
    } catch {
      throw APIError.unauthenticated("invalid or expired token");
    }
  }
});

export const gateway = new Gateway({ authHandler: auth });

export const login = api(
  { method: "POST", path: "/identity/sessions", expose: true, auth: false },
  async (params: LoginParams): Promise<LoginResult> => {
    return loginUser(params);
  }
);

export const registerUser = api(
  { method: "POST", path: "/identity/register", expose: true, auth: false },
  async (params: RegisterParams): Promise<RegisterResult> => {
    return registerUserService(params);
  }
);

export async function getMe(authData: AuthData): Promise<MeResponse> {
  return getMeProfile(authData.userID);
}

export const meEndpoint = api(
  { method: "GET", path: "/identity/me", expose: true, auth: true },
  async (): Promise<MeResponse> => {
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
    return getMeProfile(authData.userID);
  }
);
