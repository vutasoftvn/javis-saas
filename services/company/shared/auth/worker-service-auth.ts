import { APIError } from "encore.dev/api";
import jwt from "jsonwebtoken";
import { isTestRuntime } from "../env";

// Verifier duy nhất cho mọi endpoint worker/internal của Company (spec
// 2026-09-25 §5). Chỉ chấp nhận JWT do apps/cosa ký bằng
// WORKER_SERVICE_JWT_SECRET với iss/aud/role cố định; không còn so khớp chuỗi
// token thô hay secret mặc định trong handler.

export const WORKER_SERVICE_ISSUER = "apps-cosa";
export const WORKER_SERVICE_AUDIENCE = "company-internal";
const MIN_SECRET_LENGTH = 32;

export interface WorkerServiceClaims {
  iss: "apps-cosa";
  aud: "company-internal";
  sub: string; // immutable worker id
  role: "worker_service";
  exp: number;
  jti: string;
}

export interface WorkerAuthHeaders {
  authorization?: string;
  serviceToken?: string;
  "x-service-token"?: string;
}

// Fixture chỉ dùng khi chạy test (vitest) — không phải fallback của handler.
export const TEST_WORKER_SERVICE_JWT_SECRET = "test-worker-jwt-secret-min-32-chars-long-fixture";

let testSecretOverride: string | null = null;

export function setWorkerServiceSecretForTesting(secret: string | null): void {
  testSecretOverride = secret;
}

export function mintTestWorkerToken(
  sub: string = "test-worker-1",
  secret: string = TEST_WORKER_SERVICE_JWT_SECRET
): string {
  return jwt.sign(
    { role: "worker_service", jti: `jti-${Date.now()}-${Math.random()}`, sub },
    secret,
    { issuer: WORKER_SERVICE_ISSUER, audience: WORKER_SERVICE_AUDIENCE, expiresIn: "5m" }
  );
}

export function getWorkerServiceSecret(): string {
  if (testSecretOverride !== null && isTestRuntime()) {
    return testSecretOverride;
  }
  const secret = process.env.WORKER_SERVICE_JWT_SECRET ?? "";
  if (!secret && isTestRuntime()) {
    return TEST_WORKER_SERVICE_JWT_SECRET;
  }
  // Mọi môi trường ngoài test (kể cả development) phải cấu hình secret thật;
  // thiếu hoặc quá ngắn thì fail-closed trước khi chạm business lookup.
  if (secret.length < MIN_SECRET_LENGTH) {
    throw APIError.internal(
      "WORKER_SERVICE_JWT_SECRET is unconfigured or shorter than 32 characters"
    );
  }
  return secret;
}

function extractToken(headers?: WorkerAuthHeaders): string {
  const raw =
    headers?.serviceToken ||
    headers?.["x-service-token"] ||
    (headers?.authorization ? headers.authorization.replace(/^Bearer\s+/i, "") : "");
  return raw.trim();
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

export async function requireWorkerServiceAuth(
  headers?: WorkerAuthHeaders
): Promise<WorkerServiceClaims> {
  const secret = getWorkerServiceSecret();
  const token = extractToken(headers);
  if (!token) {
    throw APIError.unauthenticated("missing service token");
  }

  let decoded: string | jwt.JwtPayload;
  try {
    decoded = jwt.verify(token, secret, {
      algorithms: ["HS256"],
      audience: WORKER_SERVICE_AUDIENCE,
      issuer: WORKER_SERVICE_ISSUER,
    });
  } catch {
    throw APIError.unauthenticated("invalid or expired worker service token");
  }

  if (
    typeof decoded !== "object" ||
    decoded.iss !== WORKER_SERVICE_ISSUER ||
    decoded.aud !== WORKER_SERVICE_AUDIENCE ||
    decoded.role !== "worker_service" ||
    !isNonEmptyString(decoded.sub) ||
    !isNonEmptyString(decoded.jti) ||
    typeof decoded.exp !== "number"
  ) {
    throw APIError.unauthenticated("invalid worker service claims");
  }

  return {
    iss: WORKER_SERVICE_ISSUER,
    aud: WORKER_SERVICE_AUDIENCE,
    sub: decoded.sub,
    role: "worker_service",
    exp: decoded.exp,
    jti: decoded.jti,
  };
}
