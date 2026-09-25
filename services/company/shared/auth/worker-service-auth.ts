import { APIError } from "encore.dev/api";
import jwt from "jsonwebtoken";
import { isDevelopmentOrTest } from "../env";

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
  [key: string]: any;
}

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
    { issuer: "apps-cosa", audience: "company-internal", expiresIn: "5m" }
  );
}

export function getWorkerServiceSecret(): string {
  if (testSecretOverride !== null) {
    return testSecretOverride;
  }

  const secret = process.env.WORKER_SERVICE_JWT_SECRET;
  if (!isDevelopmentOrTest()) {
    if (!secret || secret.length < 32) {
      throw APIError.internal(
        "WORKER_SERVICE_JWT_SECRET is unconfigured or shorter than 32 characters in non-development environment"
      );
    }
    return secret;
  }

  return secret || TEST_WORKER_SERVICE_JWT_SECRET;
}

export async function requireWorkerServiceAuth(
  headers?: WorkerAuthHeaders
): Promise<WorkerServiceClaims> {
  const secret = getWorkerServiceSecret();

  const token =
    headers?.serviceToken ||
    headers?.["x-service-token"] ||
    headers?.["X-Service-Token"] ||
    (headers?.authorization ? headers.authorization.replace(/^Bearer\s+/i, "") : "");

  if (!token || !token.trim()) {
    throw APIError.unauthenticated("missing service token");
  }

  let decoded: any;
  try {
    decoded = jwt.verify(token, secret, {
      audience: "company-internal",
      issuer: "apps-cosa",
    });
  } catch {
    throw APIError.unauthenticated("invalid or expired worker service token");
  }

  if (
    !decoded ||
    typeof decoded !== "object" ||
    decoded.iss !== "apps-cosa" ||
    decoded.aud !== "company-internal" ||
    decoded.role !== "worker_service" ||
    typeof decoded.sub !== "string" ||
    !decoded.sub.trim() ||
    typeof decoded.jti !== "string" ||
    !decoded.jti.trim() ||
    typeof decoded.exp !== "number"
  ) {
    throw APIError.unauthenticated("invalid worker service claims");
  }

  return {
    iss: decoded.iss,
    aud: decoded.aud,
    sub: decoded.sub,
    role: decoded.role,
    exp: decoded.exp,
    jti: decoded.jti,
  };
}
