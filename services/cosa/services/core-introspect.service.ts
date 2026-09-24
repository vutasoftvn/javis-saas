import { APIError } from "encore.dev/api";

/**
 * Xác thực access token OIDC do `backend/core` cấp cho client `vn.mivacorp.cosa`.
 *
 * Gọi `POST {CORE_BASE_URL}/oauth/introspect` bằng client credentials của
 * confidential client `vn.mivacorp.cosa.backend` (Authorization: Basic). Core chỉ
 * cho client này hỏi token của client `vn.mivacorp.cosa` (INTROSPECTION_AUDIENCES
 * trong backend/core/auth/shared/introspect-caller-auth.ts).
 *
 * Response của core (opaque token): { active, userId, email, phone, displayName,
 * avatarUrl, clientId (id DB nội bộ), clientPublicId, scope (chuỗi cách nhau bởi
 * dấu cách), exp (giây) }.
 */

const COSA_PUBLIC_CLIENT_ID = "vn.mivacorp.cosa";
const DEFAULT_BACKEND_CLIENT_ID = "vn.mivacorp.cosa.backend";
const REQUEST_TIMEOUT_MS = 3000;
const MAX_CACHE_MS = 30_000;

export interface CoreTokenInfo {
  userId: string;
  clientId: string;
  scopes: string[];
  /** Thời điểm hết hạn của token, epoch giây. */
  expiresAt: number;
  email?: string | null;
  phone?: string | null;
  displayName?: string | null;
  avatarUrl?: string | null;
}

interface CoreIntrospectResponse {
  active: boolean;
  userId?: string;
  email?: string | null;
  phone?: string | null;
  displayName?: string | null;
  avatarUrl?: string | null;
  clientPublicId?: string;
  scope?: string;
  exp?: number;
}

interface CacheEntry {
  info: CoreTokenInfo;
  cachedUntilMs: number;
}

const cache = new Map<string, CacheEntry>();

export function clearIntrospectCache(): void {
  cache.clear();
}

function getCoreBaseUrl(): string {
  const url = process.env.CORE_BASE_URL?.trim();
  if (!url) {
    throw new Error("CORE_BASE_URL must be set (base URL of backend/core)");
  }
  return url.replace(/\/+$/, "");
}

/** Header Authorization: Basic của confidential client `vn.mivacorp.cosa.backend` (dùng cho mọi lời gọi dịch vụ tới core). */
export function getBasicAuthHeader(): string {
  const clientId = process.env.CORE_INTROSPECT_CLIENT_ID?.trim() || DEFAULT_BACKEND_CLIENT_ID;
  const secret = process.env.CORE_INTROSPECT_CLIENT_SECRET;
  if (!secret) {
    throw new Error(
      "CORE_INTROSPECT_CLIENT_SECRET must be set (run backend/core/scripts/provision-cosa-backend-client.mjs)"
    );
  }
  return "Basic " + Buffer.from(`${clientId}:${secret}`).toString("base64");
}

export async function introspectCoreToken(token: string): Promise<CoreTokenInfo> {
  if (!token) {
    throw APIError.unauthenticated("missing access token");
  }

  const now = Date.now();
  const cached = cache.get(token);
  if (cached && cached.cachedUntilMs > now) {
    return cached.info;
  }
  cache.delete(token);

  const baseUrl = getCoreBaseUrl();
  const authorization = getBasicAuthHeader();

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/oauth/introspect`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: authorization },
      body: JSON.stringify({ token }),
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch {
    throw APIError.unavailable("core introspection is unreachable");
  }

  if (response.status === 401 || response.status === 403) {
    // Core từ chối credential của chính COSA: lỗi cấu hình, không phải lỗi của user.
    throw APIError.internal("core rejected COSA introspection credentials");
  }
  if (!response.ok) {
    throw APIError.unavailable(`core introspection failed with status ${response.status}`);
  }

  const body = (await response.json()) as CoreIntrospectResponse;
  if (!body.active || !body.userId || body.clientPublicId !== COSA_PUBLIC_CLIENT_ID) {
    throw APIError.unauthenticated("invalid or expired access token");
  }

  const expiresAt = body.exp ?? Math.floor(now / 1000);
  const info: CoreTokenInfo = {
    userId: body.userId,
    clientId: body.clientPublicId,
    scopes: (body.scope ?? "").split(" ").filter((s) => s.length > 0),
    expiresAt,
    email: body.email,
    phone: body.phone,
    displayName: body.displayName,
    avatarUrl: body.avatarUrl,
  };

  const cachedUntilMs = Math.min(now + MAX_CACHE_MS, expiresAt * 1000);
  if (cachedUntilMs > now) {
    cache.set(token, { info, cachedUntilMs });
  }
  return info;
}
