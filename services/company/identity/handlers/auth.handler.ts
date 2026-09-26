import { api, Header, Gateway, APIError } from "encore.dev/api";
import { authHandler } from "encore.dev/auth";
import { verifyAccessToken, renewAccessToken } from "../services/token.service";
import { MeResponse, getMeProfile, assertLocalSessionRenewable } from "../services/auth.service";

export { MeResponse };

export interface AuthParams {
  authorization?: Header<"Authorization">;
}

export interface AuthData {
  userID: string;
  /** auth_time của local session (giây epoch) — dùng cho session epoch. */
  authTime?: number;
}

export const auth = authHandler<AuthParams, AuthData>(async (params) => {
  const header = params.authorization;
  if (!header || !header.startsWith("Bearer ")) {
    throw APIError.unauthenticated("missing bearer token");
  }
  const token = header.slice("Bearer ".length);
  try {
    const decoded = verifyAccessToken(token);
    return { userID: decoded.sub, authTime: decoded.auth_time };
  } catch {
    throw APIError.unauthenticated("invalid or expired token");
  }
});

export const gateway = new Gateway({ authHandler: auth });

export async function getMe(authData: AuthData): Promise<MeResponse> {
  return getMeProfile(authData.userID, undefined, authData.authTime);
}

export const meEndpoint = api(
  { method: "GET", path: "/identity/me", expose: true, auth: true },
  async ({ workspaceId }: { workspaceId?: Header<"X-Workspace-Id"> }): Promise<MeResponse> => {
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
    return getMeProfile(authData.userID, workspaceId, authData.authTime);
  }
);

// M1 §1 — renew local session độc lập với platform token: máy offline quá TTL 8h
// vẫn dùng được dữ liệu local đã cấp quyền; platform token hết hạn KHÔNG khoá local.
// Tuy nhiên chuỗi renewal bị giới hạn tuổi tối đa kể từ lần đăng nhập gốc
// (COMPANY_LOCAL_SESSION_MAX_AGE_SECONDS, mặc định 7 ngày) — token/renewal
// chain bị rò rỉ không thể được gia hạn vô thời hạn.
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
    let token: string;
    try {
      token = renewAccessToken(header.slice("Bearer ".length));
    } catch {
      throw APIError.unauthenticated("local session cannot be renewed");
    }
    const renewed = verifyAccessToken(token);
    await assertLocalSessionRenewable(renewed.sub, renewed.auth_time);
    return { local_session_token: token, token_type: "bearer" };
  }
);
