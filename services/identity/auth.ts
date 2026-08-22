import { Header, Gateway, APIError } from "encore.dev/api";
import { authHandler } from "encore.dev/auth";
import { verifyAccessToken } from "./token";

interface AuthParams {
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
