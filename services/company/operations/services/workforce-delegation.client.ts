import { APIError } from "encore.dev/api";
import { TenantContext } from "../../shared/types/tenant_context";

/**
 * Client Company -> Agent Platform authorization endpoint cho founder-control
 * commands (Task 6). Cùng nguồn persisted (agent.workforce_delegations) quyết
 * định một delegate có quyền hay không — KHÔNG dựa vào UI flag. Dùng secret
 * single-purpose COSA_WORKFORCE_AUTHZ_SERVICE_TOKEN.
 *
 * Fail closed: timeout, mapping principal chưa verify, workspace lệch, hoặc
 * kết quả deny => ném lỗi, lệnh founder-control không chạy tiếp.
 */

export interface DelegationAuthzQuery {
  workspaceId: string;
  principalId: string;
  platformUserId: string | null;
  action: "evaluation" | "queue_control" | "review_override";
  functionalKey: string | null;
}

export type DelegationAuthzTransport = (
  query: DelegationAuthzQuery
) => Promise<{ status: number; body: unknown }>;

const TIMEOUT_MS = 5000;

function controlPlaneUrl(): string {
  return (
    process.env.COSA_AGENTOS_INTAKE_URL ||
    process.env.PLATFORM_API_BASE_URL ||
    "http://127.0.0.1:8000"
  );
}

function serviceToken(): string {
  return process.env.COSA_WORKFORCE_AUTHZ_SERVICE_TOKEN || "dev-workforce-authz-token";
}

const defaultTransport: DelegationAuthzTransport = async (query) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${controlPlaneUrl()}/agent/internal/workforce/authorize`, {
      method: "POST",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Workforce-Authz-Token": serviceToken(),
      },
      body: JSON.stringify({
        workspace_id: query.workspaceId,
        principal_id: query.principalId,
        platform_user_id: query.platformUserId,
        action: query.action,
        functional_key: query.functionalKey,
      }),
    });
    return { status: res.status, body: await res.json().catch(() => ({})) };
  } finally {
    clearTimeout(timer);
  }
};

let transport: DelegationAuthzTransport = defaultTransport;

/** Test-only. */
export function setDelegationAuthzTransport(t: DelegationAuthzTransport | null): void {
  transport = t ?? defaultTransport;
}

/**
 * Ném lỗi nếu ctx principal không phải founder và không có delegation hợp lệ
 * cho action/functional-key. Không side-effect.
 */
export async function requireFounderOrDelegate(
  ctx: TenantContext,
  action: DelegationAuthzQuery["action"],
  functionalKey: string | null
): Promise<void> {
  if (!ctx.userId) throw APIError.unauthenticated("authentication context required");

  let res: { status: number; body: unknown };
  try {
    res = await transport({
      workspaceId: ctx.workspaceId,
      principalId: ctx.userId,
      platformUserId: ctx.platformUserId ?? null,
      action,
      functionalKey,
    });
  } catch (e) {
    throw APIError.unavailable(`workforce authorization lookup failed: ${String(e)}`);
  }

  if (res.status === 401 || res.status === 403) {
    throw APIError.permissionDenied("workforce authorization denied");
  }
  if (res.status >= 500) {
    throw APIError.unavailable(`workforce authorization returned ${res.status}`);
  }
  if (res.status !== 200) {
    throw APIError.permissionDenied(`workforce authorization rejected with ${res.status}`);
  }

  const b = (res.body ?? {}) as Record<string, unknown>;
  const data = (b.data ?? b) as Record<string, unknown>;
  if (data.workspace_id && String(data.workspace_id) !== ctx.workspaceId) {
    throw APIError.permissionDenied("workforce authorization workspace mismatch");
  }
  if (data.allowed !== true) {
    throw APIError.permissionDenied("workforce authorization denied");
  }
  if (data.mapping_verified === false) {
    throw APIError.permissionDenied("unverified principal mapping");
  }
}
