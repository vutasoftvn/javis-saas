import jwt, { SignOptions } from "jsonwebtoken";
import { APIError } from "encore.dev/api";
import { isStagingOrProd } from "../shared/env";

const DEV_PLATFORM_JWT_SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod";
const DEV_WORKER_JWT_SECRET = "cosa-worker-service-jwt-key-change-in-prod-min32chars";

export function getPlatformJwtSecret(): string {
  const secret = process.env.PLATFORM_JWT_SECRET;
  if (isStagingOrProd()) {
    if (!secret || secret === DEV_PLATFORM_JWT_SECRET || secret.length < 32) {
      throw new Error("PLATFORM_JWT_SECRET must be explicitly set with >= 32 characters in staging/production");
    }
    return secret;
  }
  return secret || DEV_PLATFORM_JWT_SECRET;
}

export function getWorkerServiceJwtSecret(): string {
  const secret = process.env.WORKER_SERVICE_JWT_SECRET;
  if (isStagingOrProd()) {
    if (!secret || secret === DEV_WORKER_JWT_SECRET || secret.length < 32) {
      throw new Error("WORKER_SERVICE_JWT_SECRET must be explicitly set with >= 32 characters in staging/production");
    }
    return secret;
  }
  return secret || process.env.PLATFORM_JWT_SECRET || DEV_WORKER_JWT_SECRET;
}

export interface PlatformJwtPayload {
  sub: string;
  aud: "cosa" | "control_plane";
  role?: string;
  workspaceId?: string;
  iss?: string;
  exp?: number;
}

export function signPlatformToken(userId: string): string {
  return jwt.sign(
    {
      sub: userId,
      aud: "cosa",
      role: "user",
      iss: "cosa_platform",
    },
    getPlatformJwtSecret(),
    {
      expiresIn: "7d",
    }
  );
}

export function signWorkerServiceToken(workerId: string, workspaceId?: string, expiresIn: SignOptions["expiresIn"] = "1d"): string {
  return jwt.sign(
    {
      sub: workerId,
      aud: "control_plane",
      role: "worker_service",
      workspaceId,
      iss: "cosa_control_plane",
    },
    getWorkerServiceJwtSecret(),
    {
      expiresIn,
    }
  );
}

export function verifyPlatformToken(token: string): PlatformJwtPayload {
  return jwt.verify(token, getPlatformJwtSecret()) as PlatformJwtPayload;
}

export function verifyWorkerServiceToken(token: string): PlatformJwtPayload {
  return jwt.verify(token, getWorkerServiceJwtSecret(), {
    audience: "control_plane",
  }) as PlatformJwtPayload;
}

export function requireWorkerServiceAuth(
  authorization: string | undefined,
  expectedWorkerId?: string
): PlatformJwtPayload {
  if (!authorization) {
    throw APIError.unauthenticated("missing authorization token");
  }
  const token = authorization.startsWith("Bearer ") ? authorization.slice(7) : authorization;
  const secret = getWorkerServiceJwtSecret();
  let payload: PlatformJwtPayload;
  try {
    payload = jwt.verify(token, secret, { audience: "control_plane" }) as PlatformJwtPayload;
  } catch {
    throw APIError.unauthenticated("invalid or expired worker service token");
  }

  // Fail-closed: Caller must have both role="worker_service" and aud="control_plane"
  if (payload.role !== "worker_service" || payload.aud !== "control_plane") {
    throw APIError.permissionDenied("forbidden: caller is not an authorized worker service");
  }

  // Cross-check identity if expectedWorkerId is specified
  if (expectedWorkerId && payload.sub !== expectedWorkerId) {
    throw APIError.permissionDenied(`forbidden: token worker identity (${payload.sub}) does not match requested worker (${expectedWorkerId})`);
  }

  return payload;
}
