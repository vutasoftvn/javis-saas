import { api, Header } from "encore.dev/api";
import { TenantContext } from "../../shared/types/tenant_context";
import { resolveTenantContext } from "../services/tenant-context.service";

export interface ResolveTenantContextRequest {
  workspaceId: string;
  correlationId?: string;
  authorization?: Header<"Authorization">;
}

/**
 * Cross-check workspace membership server-side cho caller ngoài Encore
 * (apps/cosa, Python) — bọc resolveTenantContext() đã có sẵn và đã test kỹ
 * (services/company/identity/services/tenant-context.service.ts), theo
 * COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §6.1: trước đây
 * apps/cosa chỉ verify company_id, còn workspace_id là client-provided
 * scope chưa cross-check. Giờ workspace membership là chứng minh duy nhất
 * cho product tenancy — companyId bị xoá khỏi public interface.
 */
export const resolveTenantContextEndpoint = api(
  { method: "POST", path: "/identity/tenant-context/resolve", expose: true },
  async ({
    workspaceId,
    correlationId,
    authorization,
  }: ResolveTenantContextRequest): Promise<TenantContext> => {
    return resolveTenantContext({ authorization, workspaceId, correlationId });
  }
);
