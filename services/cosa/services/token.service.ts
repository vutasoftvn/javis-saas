import jwt, { SignOptions } from "jsonwebtoken";
import { APIError } from "encore.dev/api";
import { isStagingOrProd } from "../shared/env";

const DEV_WORKER_JWT_SECRET = "cosa-worker-service-jwt-key-change-in-prod-min32chars";
// B5 fix — secret riêng cho delegation có cấu trúc chiều apps/cosa (Python,
// composition root) -> services/cosa, ký bởi
// apps/cosa/auth/jwt.py::mint_control_plane_delegation(). Đối xứng tên biến
// env với COSA_COMPANY_DELEGATION_SECRET (chiều apps/cosa -> services/company)
// nhưng KHÔNG dùng chung giá trị — 2 chiều/2 callee khác nhau.
const DEV_CONTROL_DELEGATION_SECRET = "cosa-control-delegation-dev-secret-change-in-prod";
// Secret RIÊNG cho việc ký HMAC envelope ai-governance-snapshot
// (services/cosa/services/ai-governance-snapshot.service.ts). Cố tình KHÔNG
// dùng chung COSA_CONTROL_DELEGATION_SECRET dù cùng hướng apps/cosa ->
// services/cosa: secret đó chứng minh DANH TÍNH caller (JWT ngắn hạn, TTL
// <=600s, có thể rotate độc lập theo chu kỳ auth), còn secret này chứng minh
// TÍNH TOÀN VẸN của 1 envelope có thể được lưu/forward lâu dài sang Company
// dossier layer để làm evidence — 2 mục đích khác nhau, rotate theo lịch khác
// nhau. Tái dùng 1 secret cho 2 mục đích sẽ khiến rotate secret auth vô tình
// làm mọi snapshot đã ký trước đó "tamper" giả — vi phạm CLAUDE.md "Không dùng
// đè secret này cho secret khác dù 'có vẻ tiện'".
const DEV_AI_GOVERNANCE_SIGNING_SECRET = "cosa-ai-governance-signing-dev-secret-change-in-prod";

export function getWorkerServiceJwtSecret(): string {
  const secret = process.env.WORKER_SERVICE_JWT_SECRET;
  if (isStagingOrProd()) {
    if (!secret || secret === DEV_WORKER_JWT_SECRET || secret.length < 32) {
      throw new Error("WORKER_SERVICE_JWT_SECRET must be explicitly set with >= 32 characters in staging/production");
    }
    return secret;
  }
  return secret || DEV_WORKER_JWT_SECRET;
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

export function getAiGovernanceSigningSecret(): string {
  const secret = process.env.COSA_AI_GOVERNANCE_SIGNING_SECRET;
  if (isStagingOrProd()) {
    if (!secret || secret === DEV_AI_GOVERNANCE_SIGNING_SECRET || secret.length < 32) {
      throw new Error("COSA_AI_GOVERNANCE_SIGNING_SECRET must be explicitly set with >= 32 characters in staging/production");
    }
    return secret;
  }
  return secret || DEV_AI_GOVERNANCE_SIGNING_SECRET;
}

export interface ControlDelegationPayload {
  sub: string;
  organizationId: string;
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
  const organizationId = (decoded as Record<string, unknown>).workspace_id;
  if (
    typeof decoded.sub !== "string" ||
    typeof organizationId !== "string" ||
    typeof decoded.role !== "string"
  ) {
    throw APIError.unauthenticated("control-plane delegation token missing required claims");
  }
  return { sub: decoded.sub, organizationId, role: decoded.role };
}

/** Claim của JWT dịch vụ worker (audience control_plane). Danh tính người dùng dùng access token OIDC của backend/core. */
export interface WorkerJwtPayload {
  sub: string;
  aud: "control_plane";
  role?: string;
  workspaceId?: string;
  iss?: string;
  exp?: number;
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

export function verifyWorkerServiceToken(token: string): WorkerJwtPayload {
  return jwt.verify(token, getWorkerServiceJwtSecret(), {
    audience: "control_plane",
  }) as WorkerJwtPayload;
}

export function requireWorkerServiceAuth(
  authorization: string | undefined,
  expectedWorkerId?: string
): WorkerJwtPayload {
  if (!authorization) {
    throw APIError.unauthenticated("missing authorization token");
  }
  const token = authorization.startsWith("Bearer ") ? authorization.slice(7) : authorization;
  const secret = getWorkerServiceJwtSecret();
  let payload: WorkerJwtPayload;
  try {
    payload = jwt.verify(token, secret, { audience: "control_plane" }) as WorkerJwtPayload;
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
