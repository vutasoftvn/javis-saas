import jwt, { SignOptions } from "jsonwebtoken";
import { APIError } from "encore.dev/api";
import { isStagingOrProd } from "../shared/env";

const DEV_PLATFORM_JWT_SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod";
const DEV_WORKER_JWT_SECRET = "cosa-worker-service-jwt-key-change-in-prod-min32chars";
// B5 fix — secret riêng cho delegation có cấu trúc chiều apps/cosa (Python,
// composition root) -> services/cosa, ký bởi
// apps/cosa/auth/jwt.py::mint_control_plane_delegation(). Đối xứng tên biến
// env với COSA_COMPANY_DELEGATION_SECRET (chiều apps/cosa -> services/company)
// nhưng KHÔNG dùng chung giá trị — 2 chiều/2 callee khác nhau.
const DEV_CONTROL_DELEGATION_SECRET = "cosa-control-delegation-dev-secret-change-in-prod";

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

export function getControlDelegationSecret(): string {
  const secret = process.env.COSA_CONTROL_DELEGATION_SECRET;
  if (isStagingOrProd()) {
    if (!secret || secret === DEV_CONTROL_DELEGATION_SECRET || secret.length < 32) {
      throw new Error("COSA_CONTROL_DELEGATION_SECRET must be explicitly set with >= 32 characters in staging/production");
    }
    return secret;
  }
  return secret || DEV_CONTROL_DELEGATION_SECRET;
}

export interface ControlDelegationPayload {
  sub: string;
  workspaceId: string;
  role: string;
}

/**
 * B5 fix — verify delegation JWT có cấu trúc do apps/cosa mint
 * (mint_control_plane_delegation) để thay thế việc forward Authorization
 * header sang services/company (vốn chỉ hiểu local-session token, luôn fail
 * với token platform — xem workspace-connector.service.ts::
 * verifyWorkspaceMembership). `sub` ở đây LUÔN là platform_user_id thật (đã
 * được apps/cosa cross-check với services/company trước khi mint), workspace
 * claim là workspace apps/cosa đã xác thực caller thuộc về — services/cosa
 * TIN tưởng các claim này (không re-verify lại qua company) vì chữ ký chứng
 * minh request đến từ apps/cosa (composition root đáng tin), TTL ngắn
 * (<=600s).
 *
 * Claim JWT thô là `workspace_id` (snake_case) — cùng convention với
 * mint_company_delegation/verifyCosaDelegation (services/company/shared/auth/
 * cosa-delegation.service.ts): JWT do Python mint giữ nguyên snake_case qua
 * wire, không map sang camelCase. `ControlDelegationPayload` (interface TS
 * dùng nội bộ service này) vẫn camelCase cho nhất quán với code TS xung
 * quanh — chỉ đổi tên field ngay tại điểm đọc claim.
 */
export function verifyControlDelegationToken(token: string): ControlDelegationPayload {
  let decoded: jwt.JwtPayload;
  try {
    decoded = jwt.verify(token, getControlDelegationSecret(), {
      audience: "cosa_control",
      issuer: "cosa_apps",
    }) as jwt.JwtPayload;
  } catch {
    throw APIError.unauthenticated("invalid or expired control-plane delegation token");
  }
  const workspaceId = (decoded as Record<string, unknown>).workspace_id;
  if (
    typeof decoded.sub !== "string" ||
    typeof workspaceId !== "string" ||
    typeof decoded.role !== "string"
  ) {
    throw APIError.unauthenticated("control-plane delegation token missing required claims");
  }
  return { sub: decoded.sub, workspaceId, role: decoded.role };
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
  try {
    return jwt.verify(token, getPlatformJwtSecret(), {
      audience: "cosa",
      issuer: "cosa_platform",
    }) as PlatformJwtPayload;
  } catch {
    throw APIError.unauthenticated("invalid or expired platform token");
  }
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
