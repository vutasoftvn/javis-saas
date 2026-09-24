import { APIError } from "encore.dev/api";
import { introspectCoreToken, type CoreTokenInfo } from "./core-introspect.service";
import {
  authorizeCoreOrganizationAction,
  listCoreOrganizations,
  type CoreOrganizationAction,
  type CoreOrganizationDecision,
} from "./core-organization.service";
import { mapCoreRoleToCosaRole, projectCoreAccess, projectCoreUser } from "./core-projection.service";

/**
 * Điểm vào dùng chung cho mọi nơi cần biết "ai đang gọi" và "có quyền trong organization không",
 * với hai loại bearer token trong giai đoạn chuyển tiếp: JWT platform cũ (verify cục bộ) và access
 * token OIDC của backend/core (chuỗi opaque, introspect + hỏi core; kết quả được chiếu vào DB COSA).
 */

export interface CallerIdentity {
  userId: string;
  /** Access token OIDC của core, để chuyển tiếp sang core (danh sách, quyền...). */
  accessToken: string;
}

// Access token OIDC của core là chuỗi opaque không có dấu chấm. Token có dấu chấm là JWT (delegation nội
// bộ do apps/cosa ký, được xử lý riêng ở resolveCallerAuthorizedForWorkspace), không phải danh tính người dùng.
export function looksLikeJwt(token: string): boolean {
  return token.includes(".");
}

export function stripBearer(authorization: string | undefined): string {
  if (!authorization) {
    throw APIError.unauthenticated("missing authorization header");
  }
  return authorization.replace(/^Bearer\s+/i, "");
}

function toUserProjection(info: CoreTokenInfo) {
  return {
    userId: info.userId,
    email: info.email,
    phone: info.phone,
    displayName: info.displayName,
    avatarUrl: info.avatarUrl,
  };
}

export async function resolveCallerIdentity(token: string): Promise<CallerIdentity> {
  if (!token || looksLikeJwt(token)) {
    throw APIError.unauthenticated("invalid or expired access token");
  }
  const info = await introspectCoreToken(token);
  await projectCoreUser(toUserProjection(info));
  return { userId: info.userId, accessToken: token };
}

export interface CoreAccess {
  userId: string;
  info: CoreTokenInfo;
  decision: CoreOrganizationDecision;
  role: string;
  cosaRole: string;
  membershipVersion: number;
}

/** Core quyết định quyền của user trong organization; nếu cho phép thì chiếu user, organization, role. */
export async function authorizeAndProjectCoreAccess(
  token: string,
  organizationId: string,
  action: CoreOrganizationAction
): Promise<CoreAccess> {
  const info = await introspectCoreToken(token);
  const decision = await authorizeCoreOrganizationAction(token, organizationId, action);

  await projectCoreAccess({
    user: toUserProjection(info),
    organization: {
      organizationId,
      name: decision.organizationName,
      ownerUserId: decision.ownerUserId,
    },
    role: decision.role,
  });

  return {
    userId: info.userId,
    info,
    decision,
    role: decision.role,
    cosaRole: mapCoreRoleToCosaRole(decision.role),
    membershipVersion: decision.membershipVersion,
  };
}

const CORE_ROLES_WITHOUT_COSA_ACCESS = new Set(["operator", "driver"]);

/**
 * Chiếu mọi organization COSA của user từ core vào DB COSA (mỗi organization một lần hỏi quyền để có
 * tên và chủ sở hữu). Trả về danh sách id organization; dữ liệu cũ đã bị thu hồi ở core không có mặt.
 */
export async function syncCoreMembershipsForUser(token: string): Promise<string[]> {
  const organizations = (await listCoreOrganizations(token)).filter(
    (o) => !CORE_ROLES_WITHOUT_COSA_ACCESS.has(o.role)
  );
  const ids: string[] = [];
  for (const org of organizations) {
    await authorizeAndProjectCoreAccess(token, org.organizationId, "cosa.workspace.read");
    ids.push(org.organizationId);
  }
  return ids;
}
