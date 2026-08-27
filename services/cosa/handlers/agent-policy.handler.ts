import { api, Header } from "encore.dev/api";
import { resolveAuthData } from "./auth.handler";
import {
  GetTenantPolicyParams,
  GetTenantPolicyResult,
  UpsertTenantPolicyParams,
  TenantPolicySnapshotResult,
  getTenantPolicyForTool,
  getTenantPolicySnapshotForCaller,
  upsertTenantPolicy,
} from "../services/agent-policy.service";

export { GetTenantPolicyParams, GetTenantPolicyResult, UpsertTenantPolicyParams, TenantPolicySnapshotResult };

/**
 * Internal RPC: dùng bởi `agentos` (COSA_IMPLEMENTATION roadmap Phase 10a) để
 * đọc TenantPolicy read-only trước khi đưa vào `evaluate_access()` 6 chiều —
 * business policy là business truth, thuộc `services/control-plane`, agentos
 * không tự lưu bản sao (đúng nguyên tắc CLAUDE.md §10 Local First).
 */
export const getTenantPolicy = api(
  { method: "GET", path: "/platform/internal/agent-policy", expose: false },
  async (params: GetTenantPolicyParams): Promise<GetTenantPolicyResult> => {
    return getTenantPolicyForTool(params);
  }
);

/**
 * Internal/admin RPC: cấu hình 1 rule tenant policy cho 1 company. Chưa có UI
 * admin cho endpoint này ở Phase 10 — dùng trực tiếp qua API khi cần set up
 * policy cho 1 company cụ thể (ví dụ "company X chặn mọi external write").
 */
export const setTenantPolicy = api(
  { method: "POST", path: "/platform/internal/agent-policy", expose: false },
  async (params: UpsertTenantPolicyParams): Promise<{ ok: boolean }> => {
    await upsertTenantPolicy(params);
    return { ok: true };
  }
);

export interface GetMyTenantPolicySnapshotParams {
  workspaceId: string;
  authorization?: Header<"Authorization">;
}

/**
 * Public/auth endpoint cho apps/cosa (Python, ngoài Encore) gọi qua HTTP
 * thường — khác `getTenantPolicy` (expose:false, chỉ RPC nội bộ
 * Encore-to-Encore). Verify caller thực sự thuộc workspace trước khi trả
 * policy. Resolve workspace → platform_company via services/company endpoint.
 */
export const getMyTenantPolicySnapshot = api(
  { method: "GET", path: "/platform/auth/me/agent-policy-snapshot", expose: true, auth: true },
  async (params: GetMyTenantPolicySnapshotParams): Promise<TenantPolicySnapshotResult> => {
    const authData = await resolveAuthData();
    return getTenantPolicySnapshotForCaller(authData.userID, params.workspaceId, params.authorization);
  }
);
