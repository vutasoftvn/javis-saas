import { api } from "encore.dev/api";
import {
  GetTenantPolicyParams,
  GetTenantPolicyResult,
  UpsertTenantPolicyParams,
  getTenantPolicyForTool,
  upsertTenantPolicy,
} from "../services/agent-policy.service";

export { GetTenantPolicyParams, GetTenantPolicyResult, UpsertTenantPolicyParams };

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
