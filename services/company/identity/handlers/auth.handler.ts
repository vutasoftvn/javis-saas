import { api, Header, Gateway, APIError } from "encore.dev/api";
import { authHandler } from "encore.dev/auth";
import { verifyAccessToken, renewAccessToken } from "../services/token.service";
import { MeResponse, getMeProfile } from "../services/auth.service";

export { MeResponse };

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
    throw APIError.unauthenticated("invalid or expired token");
  }
});

export const gateway = new Gateway({ authHandler: auth });

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

// M1 §1 — renew local session độc lập với platform token: máy offline quá TTL 8h
// vẫn dùng được dữ liệu local đã cấp quyền; platform token hết hạn KHÔNG khoá local.
export interface RenewLocalSessionParams {
  authorization?: Header<"Authorization">;
}
export interface RenewLocalSessionResponse {
  local_session_token: string;
  token_type: "bearer";
}

export const renewLocalSession = api(
  { method: "POST", path: "/identity/session/renew", expose: true, auth: false },
  async (params: RenewLocalSessionParams): Promise<RenewLocalSessionResponse> => {
    const header = params.authorization;
    if (!header || !header.startsWith("Bearer ")) {
      throw APIError.unauthenticated("missing bearer token");
    }
    try {
      const token = renewAccessToken(header.slice("Bearer ".length));
      return { local_session_token: token, token_type: "bearer" };
    } catch {
      throw APIError.unauthenticated("local session cannot be renewed");
    }
  }
);
