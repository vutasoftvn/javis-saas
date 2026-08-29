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

// M1 §1 — local-first: local session được renew độc lập với platform token.
// Chấp nhận token còn hạn HOẶC vừa hết hạn trong grace window (mặc định 7 ngày)
// để máy offline lâu hơn TTL vẫn dùng được dữ liệu local đã cấp quyền. Platform
// token hết hạn KHÔNG khoá local session.
function getRenewGraceSeconds(): number {
  const raw = Number(process.env.COMPANY_LOCAL_SESSION_RENEW_GRACE_SECONDS);
  return Number.isFinite(raw) && raw > 0 ? raw : 7 * 24 * 60 * 60;
}

export function renewAccessToken(token: string): string {
  let sub: string;
  try {
    sub = (jwt.verify(token, getJwtSecret()) as JwtPayload).sub;
  } catch (err) {
    if (err instanceof jwt.TokenExpiredError) {
      const decoded = jwt.verify(token, getJwtSecret(), {
        ignoreExpiration: true,
      }) as jwt.JwtPayload & JwtPayload;
      const expMs = (decoded.exp ?? 0) * 1000;
      if (Date.now() - expMs > getRenewGraceSeconds() * 1000) {
        throw new Error("local session expired beyond renewal grace window");
      }
      sub = decoded.sub;
    } else {
      throw err;
    }
  }
  if (!sub) throw new Error("local session token has no subject");
  return signAccessToken(sub);
}
