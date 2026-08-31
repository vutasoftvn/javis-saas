import jwt from "jsonwebtoken";
import { APIError } from "encore.dev/api";
import { isStagingOrProd } from "../../shared/env";

const DEV_JWT_SECRET = "cosa-dev-jwt-secret-do-not-use-in-prod";

function getJwtSecret(): string {
  const secret = process.env.JWT_SECRET;
  if (isStagingOrProd()) {
    if (!secret || secret === DEV_JWT_SECRET || secret.length < 32) {
      throw APIError.internal("JWT_SECRET must be explicitly set with >= 32 characters in staging/production");
    }
    return secret;
  }
  return secret || DEV_JWT_SECRET;
}

export interface JwtPayload {
  sub: string;
  auth_time: number;
}

function getSessionTtl(): string {
  return process.env.COMPANY_LOCAL_SESSION_TTL?.trim() || "8h";
}

// Giới hạn tuổi tối đa của một chuỗi renewal (tính từ lần đăng nhập gốc, không
// phải từ lần renew gần nhất) — chặn kịch bản renewal chain bị rò rỉ/đánh cắp
// thì không bao giờ hết hạn thật sự. Mặc định 7 ngày, cấu hình qua env.
function getMaximumSessionAgeSeconds(): number {
  const raw = Number(process.env.COMPANY_LOCAL_SESSION_MAX_AGE_SECONDS);
  return Number.isFinite(raw) && raw > 0 ? raw : 7 * 24 * 60 * 60;
}

export function signAccessToken(userId: string, authTime: number = Math.floor(Date.now() / 1000)): string {
  return jwt.sign({ sub: userId, auth_time: authTime }, getJwtSecret(), { expiresIn: getSessionTtl() as any });
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
  let authTime: number | undefined;
  try {
    const decoded = jwt.verify(token, getJwtSecret()) as jwt.JwtPayload & JwtPayload;
    sub = decoded.sub;
    authTime = decoded.auth_time;
  } catch (err) {
    if (err instanceof jwt.TokenExpiredError) {
      const decoded = jwt.verify(token, getJwtSecret(), {
        ignoreExpiration: true,
      }) as jwt.JwtPayload & JwtPayload;
      const expMs = (decoded.exp ?? 0) * 1000;
      if (Date.now() - expMs > getRenewGraceSeconds() * 1000) {
        throw APIError.unauthenticated("local session expired beyond renewal grace window");
      }
      sub = decoded.sub;
      authTime = decoded.auth_time;
    } else {
      throw err;
    }
  }
  if (!sub) throw APIError.unauthenticated("local session token has no subject");
  // Chặn renewal chain vượt quá tuổi tối đa kể từ lần đăng nhập gốc — token
  // cũ trước khi có claim auth_time (authTime === undefined) được coi như vừa
  // đăng nhập lại để không phá vỡ session đang hoạt động của người dùng cũ.
  if (authTime !== undefined && Date.now() / 1000 - authTime > getMaximumSessionAgeSeconds()) {
    throw APIError.unauthenticated("local session exceeds maximum age");
  }
  return signAccessToken(sub, authTime);
}
