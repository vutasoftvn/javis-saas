import { APIError } from "encore.dev/api";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import { TenantContext } from "../types/tenant_context";

/**
 * Xác nhận caller (qua Bearer token) thực sự là thành viên của workspaceId
 * được truy cập, trước khi đọc/ghi dữ liệu nghiệp vụ. Throw APIError.unauthenticated
 * nếu thiếu/sai token, permissionDenied nếu không thuộc workspace này.
 *
 * Dùng cho MỌI endpoint đọc/ghi dữ liệu theo workspace ở finance-legal,
 * commercial, operations — trước đây các endpoint này hoàn toàn không xác
 * thực (Encore mặc định `auth: false` khi không khai báo), chỉ dựa vào
 * `workspaceId` trong request mà không kiểm tra ai đang gọi.
 *
 * CRITICAL: Nhận workspaceId dưới dạng string | number. Truyền thẳng xuống
 * resolveTenantContext() mà không dùng Number()/parseInt() — những hàm này
 * gây mất độ chính xác trên Snowflake ID 18-19 chữ số. Hàm resolveTenantContext
 * tự xử lý conversion an toàn qua BigInt() ở tầng DB.
 *
 * NOTE: workspaceId là bắt buộc. Không có fallback để lookup workspace từ
 * companyId hay chọn workspace mặc định — caller phải cung cấp workspace
 * rõ ràng.
 */
export interface WorkspaceAccessOptions {
  /**
   * Capability id của agent được phép gọi endpoint này bằng delegation token
   * (xem `resolveTenantContext`). Bỏ trống ⇒ chỉ phiên đăng nhập của người dùng.
   */
  agentCapabilities?: readonly string[];
}

export async function requireWorkspaceAccess(
  authorization: string | undefined,
  workspaceId: string | number,
  options: WorkspaceAccessOptions = {}
): Promise<TenantContext> {
  return resolveTenantContext({
    authorization,
    workspaceId,
    agentCapabilities: options.agentCapabilities,
  });
}

/**
 * Như `requireWorkspaceAccess` nhưng chặn role chỉ đọc (auditor và role lạ,
 * xem `getRolePermissions`). Dùng cho endpoint ghi dữ liệu nghiệp vụ.
 */
export async function requireWorkspaceWrite(
  authorization: string | undefined,
  workspaceId: string | number,
  options: WorkspaceAccessOptions = {}
): Promise<TenantContext> {
  const ctx = await requireWorkspaceAccess(authorization, workspaceId, options);
  if (!ctx.permissions.includes("*") && !ctx.permissions.includes("write")) {
    throw APIError.permissionDenied("role hiện tại chỉ có quyền đọc trong workspace này");
  }
  return ctx;
}

export { requireFounderCommand } from "../../identity/services/command-authority.service";
