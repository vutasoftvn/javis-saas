import { api, Header } from "encore.dev/api";
import { resolveCallerAuthorizedForWorkspace } from "../services/workspace-connector.service";
import {
  GetTenantPolicyParams,
  GetTenantPolicyResult,
  UpsertTenantPolicyParams,
  TenantPolicySnapshotResult,
  buildTenantPolicySnapshot,
  getTenantPolicyForTool,
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
 *
 * B5 fix (2026-09-04) — trước đây dùng `auth: true` (Encore Gateway, chỉ
 * chấp nhận PLATFORM_JWT_SECRET) rồi verify membership bằng cách forward
 * Authorization sang services/company (chỉ hiểu JWT_SECRET local-session) —
 * 2 secret khác nhau nên KHÔNG token nào qua được cả 2 chặng, mọi request từ
 * apps/cosa đều fail 403 permission_denied vô điều kiện. Giờ tự verify thủ
 * công qua `resolveCallerAuthorizedForWorkspace` (dùng chung với
 * workspace-schedule.handler.ts) — ưu tiên control-plane delegation, fallback
 * platform token gốc + verifyWorkspaceMembership (giữ nguyên hành vi cũ cho
 * caller nào không dùng delegation).
 */
export const getMyTenantPolicySnapshot = api(
  { method: "GET", path: "/platform/auth/me/agent-policy-snapshot", expose: true, auth: false },
  async (params: GetMyTenantPolicySnapshotParams): Promise<TenantPolicySnapshotResult> => {
    const caller = await resolveCallerAuthorizedForWorkspace(params.authorization, params.workspaceId);
    return buildTenantPolicySnapshot(caller.sub, params.workspaceId);
  }
);
