import { api, APIError } from "encore.dev/api";
import { identityDB } from "./db";
import { verifyPassword } from "./password";
import { signAccessToken } from "./token";

export interface LoginParams {
  email: string;
  password: string;
}

export interface LoginResult {
  accessToken: string;
}

export const login = api(
  { method: "POST", path: "/identity/sessions", expose: true },
  async (params: LoginParams): Promise<LoginResult> => {
    const email = params.email.trim().toLowerCase();
    const row = await identityDB.queryRow<{ id: number; password_hash: string | null }>`
      SELECT id, password_hash FROM core.users WHERE email = ${email}
    `;
    if (!row || !row.password_hash) {
      throw APIError.unauthenticated("sai email hoặc mật khẩu");
    }
    const valid = await verifyPassword(params.password, row.password_hash);
    if (!valid) {
      throw APIError.unauthenticated("sai email hoặc mật khẩu");
    }
    return { accessToken: signAccessToken(String(row.id)) };
  }
);
