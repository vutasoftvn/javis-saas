import { APIError } from "encore.dev/api";
import { CAS_CONTRACT, type CasRawTransaction } from "./cas-contract";

const REQUEST_TIMEOUT_MS = 30_000;

// IA09 — xác nhận qua tài liệu công khai thật của cas.so (WebFetch, không
// đoán): MỌI request tới cas.so (kể cả GET /transactions bằng accessToken)
// đều cần thêm 2 header developer credentials + version header, KHÔNG chỉ
// dùng Authorization. Trước đây cas-client.ts hoàn toàn thiếu 3 header này.
export interface CasClientConfig {
  accessToken: string;
  environment: "sandbox" | "production";
  clientId: string;
  secretKey: string;
}

function getCasBaseUrl(env: "sandbox" | "production"): string {
  if (env === "sandbox") {
    return CAS_CONTRACT.baseUrls.sandbox;
  }
  // Production not ready yet
  throw APIError.failedPrecondition(
    "CAS_PROVIDER_NOT_READY: Cas.so production endpoint not confirmed. Provider status: NOT_READY"
  );
}

async function casRequest<T>(
  config: Pick<CasClientConfig, "accessToken" | "environment" | "clientId" | "secretKey">,
  path: string,
  opts?: { method?: string; body?: unknown }
): Promise<T> {
  const baseUrl = getCasBaseUrl(config.environment);
  const url = `${baseUrl}${path}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      method: opts?.method || "GET",
      headers: {
        // IA09 — tài liệu curl mẫu xác nhận Authorization là accessToken
        // TRẦN, KHÔNG có tiền tố "Bearer " (khác quy ước JWT thông thường).
        Authorization: config.accessToken,
        [CAS_CONTRACT.apiVersionHeader]: CAS_CONTRACT.contractVersion,
        [CAS_CONTRACT.auth.developerHeaders.clientId]: config.clientId,
        [CAS_CONTRACT.auth.developerHeaders.secretKey]: config.secretKey,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: opts?.body ? JSON.stringify(opts.body) : undefined,
      signal: controller.signal,
    });

    if (response.status === 401 || response.status === 403) {
      throw APIError.permissionDenied(
        `CAS_GRANT_REVOKED: Cas.so returned ${response.status}. Grant may be revoked or expired.`
      );
    }

    if (response.status === 429) {
      const retryAfter = response.headers.get("Retry-After") || "60";
      throw APIError.resourceExhausted(
        `CAS_RATE_LIMITED: Retry after ${retryAfter}s`
      );
    }

    if (!response.ok) {
      throw APIError.internal(
        `CAS_HTTP_ERROR: ${response.status} ${response.statusText} from Cas.so`
      );
    }

    return (await response.json()) as T;
  } catch (err: any) {
    if (err?.name === "AbortError") {
      throw APIError.deadlineExceeded(`CAS_TIMEOUT: Request to Cas.so timed out after ${REQUEST_TIMEOUT_MS}ms`);
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export interface CasTransactionPage {
  transactions: CasRawTransaction[];
  nextCursor: string | null;
  hasMore: boolean;
}

/**
 * GET transactions from Cas.so with cursor-based pagination.
 * Safe to retry on GET.
 */
export async function casGetTransactions(
  config: CasClientConfig,
  opts?: {
    cursor?: string;
    limit?: number;
    fromDate?: string; // YYYY-MM-DD
    toDate?: string;
  }
): Promise<CasTransactionPage> {
  const params = new URLSearchParams();
  if (opts?.cursor) params.set("cursor", opts.cursor);
  if (opts?.limit) params.set("limit", String(opts.limit));
  if (opts?.fromDate) params.set("from_date", opts.fromDate);
  if (opts?.toDate) params.set("to_date", opts.toDate);

  const path = `/transactions${params.size > 0 ? `?${params.toString()}` : ""}`;

  // IA09 — response body/pagination fields của GET /transactions KHÔNG xác
  // nhận được qua tài liệu công khai (trang docs dùng UI tương tác, không
  // trả về ví dụ raw JSON qua WebFetch). Giữ nguyên parse "data"/"pagination"
  // như cũ (chưa xác nhận đúng/sai) — KHÔNG đoán field mới để tránh thay một
  // giả định chưa kiểm chứng bằng một giả định chưa kiểm chứng khác.
  const raw = await casRequest<{
    data: CasRawTransaction[];
    pagination?: { next_cursor?: string; has_more?: boolean };
  }>(config, path);

  return {
    transactions: raw.data || [],
    nextCursor: raw.pagination?.next_cursor || null,
    hasMore: raw.pagination?.has_more || false,
  };
}

/**
 * Token exchange — KHÔNG retry mù sau kết quả không chắc.
 * Chỉ gọi một lần; lưu kết quả vào secret store.
 *
 * IA09 — path/body xác nhận qua tài liệu công khai thật (WebFetch):
 * POST /grant/exchange (KHÔNG phải /tokens/exchange), body {publicToken}
 * camelCase (KHÔNG phải {public_token} snake_case), kèm 3 header developer
 * credentials như mọi endpoint khác. Response field casing của endpoint NÀY
 * cụ thể không có ví dụ raw JSON xác nhận được — nhưng endpoint chị em
 * /grant/token (đã xác nhận, xem createCasLinkSessionService) trả về
 * camelCase (`grantToken`), nên ưu tiên đọc camelCase, fallback snake_case
 * để không vỡ nếu provider dùng casing khác — không loại trừ khả năng nào
 * khi chưa có evidence trực tiếp.
 */
export async function casExchangePublicToken(
  publicToken: string,
  environment: "sandbox" | "production",
  credentials: { clientId: string; secretKey: string }
): Promise<{ accessToken: string; grantId: string; expiresAt: string }> {
  // NOTE: Đây là idempotent exchange chỉ dùng một lần sau OAuth redirect.
  // Không retry nếu kết quả không chắc (e.g., 200 nhưng không có token).
  const baseUrl = getCasBaseUrl(environment);
  const url = `${baseUrl}/grant/exchange`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      [CAS_CONTRACT.apiVersionHeader]: CAS_CONTRACT.contractVersion,
      [CAS_CONTRACT.auth.developerHeaders.clientId]: credentials.clientId,
      [CAS_CONTRACT.auth.developerHeaders.secretKey]: credentials.secretKey,
    },
    body: JSON.stringify({ publicToken }),
  });

  if (!response.ok) {
    throw APIError.failedPrecondition(
      `CAS_EXCHANGE_FAILED: ${response.status} ${response.statusText}`
    );
  }

  const data = (await response.json()) as any;
  const accessToken = data.accessToken ?? data.access_token;
  const grantId = data.grantId ?? data.grant_id;
  const expiresAt = data.expiresAt ?? data.expires_at;

  if (!accessToken || !grantId) {
    throw APIError.internal("CAS_EXCHANGE_INCOMPLETE: Missing accessToken or grantId in response");
  }

  return {
    accessToken,
    grantId,
    expiresAt: expiresAt || new Date(Date.now() + 90 * 24 * 3600 * 1000).toISOString(),
  };
}
