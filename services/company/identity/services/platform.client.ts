import { APIError } from "encore.dev/api";
import { isStagingOrProd } from "../../shared/env";

const DEV_PLATFORM_URL = "http://127.0.0.1:4001";
const PLATFORM_REQUEST_TIMEOUT_MS = 5000;

export function getPlatformUrl(): string {
  const url = process.env.PLATFORM_API_BASE_URL;
  if (isStagingOrProd()) {
    if (!url || url === DEV_PLATFORM_URL) {
      throw APIError.internal("PLATFORM_API_BASE_URL must be explicitly set in staging/production, cannot use default URL");
    }
    return url;
  }
  return url || DEV_PLATFORM_URL;
}

// Access token OIDC của backend/core là chuỗi opaque không có dấu chấm; token có dấu chấm (JWT) không phải
// danh tính người dùng. Token do control-plane (cosa) xác thực qua backend/core.
function isJwtShaped(token: string): boolean {
  return token.includes(".");
}

export interface PlatformIdentity {
  userId: string;
  email?: string | null;
  displayName?: string | null;
}

/**
 * Danh tính của người giữ access token OIDC của core: hỏi control-plane (cosa)
 * `POST /platform/internal/resolve-identity`, nơi introspect thật với backend/core.
 */
export async function resolvePlatformIdentity(token: string): Promise<PlatformIdentity> {
  if (!token || isJwtShaped(token)) {
    throw APIError.unauthenticated("invalid or expired access token");
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), PLATFORM_REQUEST_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(`${getPlatformUrl()}/platform/internal/resolve-identity`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platformToken: token }),
      signal: controller.signal,
    });
  } catch (err) {
    throw APIError.unavailable(
      "không thể xác thực danh tính với control-plane (cosa) — thử lại sau",
      err instanceof Error ? err : undefined
    );
  } finally {
    clearTimeout(timeout);
  }

  if (res.status === 401 || res.status === 403) {
    throw APIError.unauthenticated("invalid or expired access token");
  }
  if (!res.ok) {
    throw APIError.unavailable(`control-plane trả về lỗi không mong đợi: HTTP ${res.status}`);
  }
  const data = (await res.json()) as PlatformIdentity;
  if (!data.userId) {
    throw APIError.unavailable("control-plane không trả về userId");
  }
  return data;
}

/**
 * Xác thực membership của user trong 1 company qua RPC HTTP sang `services/cosa`
 * (nguồn sự thật duy nhất cho tenancy — xem CLAUDE.md §11 và
 * docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md mục "control-plane vs identity").
 *
 * QUAN TRỌNG: chữ ký JWT hợp lệ chỉ chứng minh danh tính (identity), KHÔNG chứng
 * minh user đó thuộc company này hay có role gì. Nếu `cosa` không phản hồi được
 * (mất mạng local<->VPS, VPS down, timeout), hàm này PHẢI fail-closed
 * (`APIError.unavailable`) — tuyệt đối không được tự suy ra role/membership từ
 * JWT rồi mặc định "founder", vì đó là leo thang đặc quyền: bất kỳ ai có access
 * token hợp lệ sẽ tự phong mình làm founder của bất kỳ company nào ngay khi
 * đường truyền tới control-plane gián đoạn.
 */


export interface PlatformWorkspaceMembership {
  platformWorkspaceId: string;
  workspaceName: string;
  userId: string;
  email: string | null;
  displayName: string | null;
  role: string;
  membershipId: string;
  membershipUpdatedAt: string;
}

export async function listPlatformWorkspaceMemberships(params: {
  platformToken: string;
}): Promise<PlatformWorkspaceMembership[]> {

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), PLATFORM_REQUEST_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(`${getPlatformUrl()}/platform/internal/list-workspace-memberships`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${params.platformToken}`,
      },
      body: JSON.stringify({
        platformToken: params.platformToken,
      }),
      signal: controller.signal,
    });
  } catch (err) {
    throw APIError.unavailable(
      "không thể lấy danh sách workspace memberships từ control-plane (cosa) — thử lại sau",
      err instanceof Error ? err : undefined
    );
  } finally {
    clearTimeout(timeout);
  }

  if (res.status === 401 || res.status === 403) {
    throw APIError.permissionDenied("user không có quyền");
  }
  if (!res.ok) {
    throw APIError.unavailable(`control-plane trả về lỗi không mong đợi: HTTP ${res.status}`);
  }

  const data = (await res.json()) as { memberships?: PlatformWorkspaceMembership[] };
  return data.memberships || [];
}

export async function validatePlatformWorkspaceMembership(params: {
  platformToken: string;
  platformWorkspaceId: string;
}): Promise<PlatformWorkspaceMembership & { valid: boolean }> {

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), PLATFORM_REQUEST_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(`${getPlatformUrl()}/platform/internal/validate-workspace-membership`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${params.platformToken}`,
      },
      body: JSON.stringify({
        platformToken: params.platformToken,
        platformWorkspaceId: params.platformWorkspaceId,
      }),
      signal: controller.signal,
    });
  } catch (err) {
    throw APIError.unavailable(
      "không thể xác thực workspace membership với control-plane (cosa) — thử lại sau",
      err instanceof Error ? err : undefined
    );
  } finally {
    clearTimeout(timeout);
  }

  if (res.status === 401 || res.status === 403) {
    throw APIError.permissionDenied("user không có quyền truy cập workspace này");
  }
  if (res.status === 404) {
    throw APIError.notFound("workspace hoặc membership không tồn tại");
  }
  if (!res.ok) {
    throw APIError.unavailable(`control-plane trả về lỗi không mong đợi: HTTP ${res.status}`);
  }

  const data = (await res.json()) as { valid: boolean; membership?: PlatformWorkspaceMembership };
  if (!data.valid || !data.membership) {
    throw APIError.permissionDenied("user không có quyền truy cập workspace này");
  }
  return {
    ...data.membership,
    valid: true,
  };
}

export async function markPlatformWorkspaceSynced(params: {
  platformWorkspaceId: string;
  platformToken: string;
}): Promise<void> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), PLATFORM_REQUEST_TIMEOUT_MS);

  try {
    await fetch(`${getPlatformUrl()}/platform/internal/mark-workspace-synced`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${params.platformToken}`,
      },
      body: JSON.stringify({
        platformWorkspaceId: params.platformWorkspaceId,
        platformToken: params.platformToken,
      }),
      signal: controller.signal,
    });
  } catch {
    // Non-blocking callback
  } finally {
    clearTimeout(timeout);
  }
}

