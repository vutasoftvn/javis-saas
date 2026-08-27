import jwt from "jsonwebtoken";
import { isStagingOrProd } from "../../shared/env";

const DEV_JWT_SECRET = "cosa-dev-jwt-secret-do-not-use-in-prod";

function getJwtSecret(): string {
  const secret = process.env.JWT_SECRET;
  if (isStagingOrProd()) {
    if (!secret || secret === DEV_JWT_SECRET || secret.length < 32) {
      throw new Error("JWT_SECRET must be explicitly set with >= 32 characters in staging/production");
    }
    return secret;
  }
  return secret || DEV_JWT_SECRET;
}

export interface JwtPayload {
  sub: string;
}

function getSessionTtl(): string {
  return process.env.COMPANY_LOCAL_SESSION_TTL?.trim() || "8h";
}

export function signAccessToken(userId: string): string {
  return jwt.sign({ sub: userId }, getJwtSecret(), { expiresIn: getSessionTtl() as any });
}

export function verifyAccessToken(token: string): JwtPayload {
  return jwt.verify(token, getJwtSecret()) as JwtPayload;
}
