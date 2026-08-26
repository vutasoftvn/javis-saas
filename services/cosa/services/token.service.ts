import jwt from "jsonwebtoken";
import { APIError } from "encore.dev/api";

const JWT_SECRET = process.env.PLATFORM_JWT_SECRET || "cosa-super-secret-platform-jwt-key-change-in-prod";

export interface PlatformJwtPayload {
  sub: string;
  aud: "cosa" | "control_plane";
  role?: string;
  workspaceId?: string;
}

export function signPlatformToken(userId: string): string {
  return jwt.sign(
    {
      sub: userId,
      aud: "cosa",
      role: "user",
    },
    JWT_SECRET,
    {
      expiresIn: "7d",
    }
  );
}

export function signWorkerServiceToken(workerId: string, workspaceId?: string): string {
  return jwt.sign(
    {
      sub: workerId,
      aud: "control_plane",
      role: "worker_service",
      workspaceId,
    },
    JWT_SECRET,
    {
      expiresIn: "1d",
    }
  );
}

export function verifyPlatformToken(token: string): PlatformJwtPayload {
  return jwt.verify(token, JWT_SECRET) as PlatformJwtPayload;
}

export function requireWorkerServiceAuth(authorization: string | undefined): PlatformJwtPayload {
  if (!authorization) {
    throw APIError.unauthenticated("missing authorization token");
  }
  const token = authorization.startsWith("Bearer ") ? authorization.slice(7) : authorization;
  let payload: PlatformJwtPayload;
  try {
    payload = verifyPlatformToken(token);
  } catch {
    throw APIError.unauthenticated("invalid or expired worker service token");
  }

  if (payload.role !== "worker_service" && payload.aud !== "control_plane") {
    throw APIError.permissionDenied("forbidden: caller is not an authorized worker service");
  }

  return payload;
}
