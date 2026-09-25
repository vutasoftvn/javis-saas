import { APIError } from "encore.dev/api";
import { getBasicAuthHeader } from "./core-introspect.service";

/**
 * Kiểm tra quyền của user trong organization bằng backend/core.
 *
 * Chuyển tiếp CHÍNH bearer token OIDC của user tới
 * `POST {CORE_BASE_URL}/me/organizations/:organizationId/authorize`; core lấy subject từ
 * token nên COSA không cần credential dịch vụ riêng và không thể hỏi hộ người khác.
 * Ma trận role -> action nằm ở core (organization/services/role-matrix.ts), COSA không nhân đôi.
 */

const REQUEST_TIMEOUT_MS = 3000;

export type CoreOrganizationAction =
  | "cosa.workspace.read"
  | "cosa.workspace.write"
  | "cosa.workspace.manage_members"
  | "cosa.workspace.manage_billing";

export interface CoreOrganizationDecision {
  role: string;
  membershipVersion: number;
  typeCode: string | null;
  organizationName: string;
  ownerUserId: string;
}

interface CoreAuthorizeResponse {
  allowed?: boolean;
  role?: string;
  membershipVersion?: number;
  typeCode?: string | null;
  organizationName?: string;
  ownerUserId?: string;
}

function getCoreBaseUrl(): string {
  const url = process.env.CORE_BASE_URL?.trim();
  if (!url) {
    throw new Error("CORE_BASE_URL must be set (base URL of backend/core)");
  }
  return url.replace(/\/+$/, "");
}

export interface CoreOrganizationSummary {
  organizationId: string;
  name: string;
  role: string;
}

/** Danh sách organization đang active của user (GET /me/organizations) theo bearer của chính user. */
export async function listCoreOrganizations(accessToken: string): Promise<CoreOrganizationSummary[]> {
  let response: Response;
  try {
    response = await fetch(`${getCoreBaseUrl()}/me/organizations`, {
      method: "GET",
      headers: { Authorization: `Bearer ${accessToken}` },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch {
    throw APIError.unavailable("core organization service is unreachable");
  }

  if (response.status === 401) {
    throw APIError.unauthenticated("invalid or expired access token");
  }
  if (!response.ok) {
    throw APIError.unavailable(`core organization listing failed with status ${response.status}`);
  }

  const body = (await response.json()) as {
    organizations?: Array<{ organizationId: string; name: string; role: string; isActive?: boolean }>;
  };
  return (body.organizations ?? [])
    .filter((o) => o.isActive !== false)
    .map((o) => ({ organizationId: String(o.organizationId), name: o.name, role: o.role }));
}

/**
 * Tạo organization ở core bằng bearer của chính user (POST /companies). Không có taxCode/typeId
 * nên core ghi `legal_status = unregistered`; người tạo là `founder`. id organization do core sinh.
 */
export async function createCoreOrganization(
  accessToken: string,
  name: string
): Promise<{ organizationId: string; name: string }> {
  let response: Response;
  try {
    response = await fetch(`${getCoreBaseUrl()}/companies`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ name, creatorRole: "founder" }),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch {
    throw APIError.unavailable("core organization service is unreachable");
  }

  if (response.status === 401) {
    throw APIError.unauthenticated("invalid or expired access token");
  }
  if (response.status === 400) {
    throw APIError.invalidArgument("core rejected the organization details");
  }
  if (!response.ok) {
    throw APIError.unavailable(`core organization creation failed with status ${response.status}`);
  }

  const body = (await response.json()) as { id?: string; name?: string };
  if (!body.id) {
    throw APIError.unavailable("core organization creation returned no id");
  }
  return { organizationId: String(body.id), name: body.name ?? name };
}

/**
 * Cấp membership ở core thay cho người dùng (POST /internal/organizations/:id/members) bằng
 * client credentials của backend COSA. Chỉ gọi sau khi COSA đã xác thực lời mời hợp lệ.
 * Core chỉ nhận role member/admin/viewer và idempotent: người đã là thành viên giữ nguyên role,
 * response trả role hiện tại để COSA đồng bộ bản chiếu.
 */
/** Kết quả cấp membership ở core; `membershipVersion` có khi core trả về. */
export interface CoreMembershipGrant {
  role: string;
  membershipVersion?: number;
}

export async function grantCoreMembership(
  organizationId: string,
  userId: string,
  role: string
): Promise<CoreMembershipGrant> {
  const authorization = getBasicAuthHeader();
  const url = `${getCoreBaseUrl()}/internal/organizations/${encodeURIComponent(organizationId)}/members`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: authorization },
      body: JSON.stringify({ userId, role }),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch {
    throw APIError.unavailable("core membership service is unreachable");
  }

  if (response.status === 401 || response.status === 403) {
    // Core từ chối credential của chính COSA: lỗi cấu hình, không phải lỗi của user.
    throw APIError.internal("core rejected COSA service credentials");
  }
  if (response.status === 404) {
    throw APIError.notFound(`organization ${organizationId} does not exist in core`);
  }
  if (!response.ok) {
    throw APIError.unavailable(`core membership grant failed with status ${response.status}`);
  }

  const body = (await response.json()) as { role?: string; membershipVersion?: number };
  return {
    role: body.role ?? role,
    ...(typeof body.membershipVersion === "number" ? { membershipVersion: body.membershipVersion } : {}),
  };
}

export async function authorizeCoreOrganizationAction(
  accessToken: string,
  organizationId: string,
  action: CoreOrganizationAction
): Promise<CoreOrganizationDecision> {
  const url = `${getCoreBaseUrl()}/me/organizations/${encodeURIComponent(organizationId)}/authorize`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ action }),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch {
    throw APIError.unavailable("core organization authorization is unreachable");
  }

  if (response.status === 401) {
    throw APIError.unauthenticated("invalid or expired access token");
  }
  if (response.status === 403 || response.status === 404) {
    throw APIError.permissionDenied(`user does not have access to organization ${organizationId}`);
  }
  if (!response.ok) {
    throw APIError.unavailable(`core organization authorization failed with status ${response.status}`);
  }

  const body = (await response.json()) as CoreAuthorizeResponse;
  if (!body.allowed || !body.role) {
    throw APIError.permissionDenied(`user does not have access to organization ${organizationId}`);
  }

  if (!body.organizationName || !body.ownerUserId) {
    throw APIError.unavailable("core authorization response is missing organization details");
  }

  return {
    role: body.role,
    membershipVersion: body.membershipVersion ?? 1,
    typeCode: body.typeCode ?? null,
    organizationName: body.organizationName,
    ownerUserId: body.ownerUserId,
  };
}
