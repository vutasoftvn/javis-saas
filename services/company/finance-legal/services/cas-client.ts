import { APIError } from "encore.dev/api";
import { CAS_CONTRACT, type CasRawTransaction } from "./cas-contract";

const REQUEST_TIMEOUT_MS = 30_000;

export interface CasClientConfig {
  accessToken: string;
  environment: "sandbox" | "production";
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
  accessToken: string,
  env: "sandbox" | "production",
  path: string,
  opts?: { method?: string; body?: unknown }
): Promise<T> {
  const baseUrl = getCasBaseUrl(env);
  const url = `${baseUrl}${path}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      method: opts?.method || "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
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

  const raw = await casRequest<{
    data: CasRawTransaction[];
    pagination?: { next_cursor?: string; has_more?: boolean };
  }>(config.accessToken, config.environment, path);

  return {
    transactions: raw.data || [],
    nextCursor: raw.pagination?.next_cursor || null,
    hasMore: raw.pagination?.has_more || false,
  };
}

/**
 * Token exchange — KHÔNG retry mù sau kết quả không chắc.
 * Chỉ gọi một lần; lưu kết quả vào secret store.
 */
export async function casExchangePublicToken(
  publicToken: string,
  environment: "sandbox" | "production"
): Promise<{ accessToken: string; grantId: string; expiresAt: string }> {
  // NOTE: Đây là idempotent exchange chỉ dùng một lần sau OAuth redirect.
  // Không retry nếu kết quả không chắc (e.g., 200 nhưng không có token).
  const baseUrl = getCasBaseUrl(environment);
  const url = `${baseUrl}/tokens/exchange`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ public_token: publicToken }),
  });

  if (!response.ok) {
    throw APIError.failedPrecondition(
      `CAS_EXCHANGE_FAILED: ${response.status} ${response.statusText}`
    );
  }

  const data = await response.json() as any;

  if (!data.access_token || !data.grant_id) {
    throw APIError.internal("CAS_EXCHANGE_INCOMPLETE: Missing access_token or grant_id in response");
  }

  return {
    accessToken: data.access_token,
    grantId: data.grant_id,
    expiresAt: data.expires_at || new Date(Date.now() + 90 * 24 * 3600 * 1000).toISOString(),
  };
}
