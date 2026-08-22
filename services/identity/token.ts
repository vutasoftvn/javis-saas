import jwt from "jsonwebtoken";
import { secret } from "encore.dev/config";

const jwtSecret = secret("IdentityJwtSecret");

function getSecret(): string {
  return jwtSecret() || process.env.IDENTITY_JWT_SECRET || "dev-local-secret-do-not-use-in-prod";
}

export interface AccessTokenPayload {
  sub: string;
}

export function signAccessToken(userId: string, expiresInMinutes = 60 * 24 * 7): string {
  return jwt.sign({ sub: userId }, getSecret(), {
    algorithm: "HS256",
    expiresIn: `${expiresInMinutes}m`,
  });
}

export function verifyAccessToken(token: string): AccessTokenPayload {
  const decoded = jwt.verify(token, getSecret(), { algorithms: ["HS256"] });
  if (typeof decoded === "string" || !decoded.sub) {
    throw new Error("invalid token payload");
  }
  return { sub: decoded.sub as string };
}
