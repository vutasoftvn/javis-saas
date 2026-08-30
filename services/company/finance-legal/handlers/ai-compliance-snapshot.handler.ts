import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  captureComplianceSnapshot,
  verifySnapshotIntegrity,
  listSnapshots,
} from "../services/ai-compliance-snapshot.service";

export interface CaptureSnapshotRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface VerifySnapshotRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
  id: string;
}

export interface ListSnapshotsRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

// Non-exposed internal snapshot route as required by plan.
//
// Task 4 fix: trước đây gọi `captureComplianceSnapshot(ctx.workspaceId,
// ctx.workforceMemberId || ctx.userId)` — tham số thứ 2 của
// captureComplianceSnapshot là deploymentIdInput, KHÔNG PHẢI member id. Vì
// memberId gần như không bao giờ trùng 1 deployment id thật, mọi lệnh gọi
// route này trước đây luôn rơi vào nhánh "deployment không tìm thấy" của
// code cũ — chính là nhánh tự tạo deployment/assessment/APPROVED mặc định
// (lỗ hổng đã xác nhận, xem task-4-brief.md). Giờ đây captureComplianceSnapshot
// không còn tự tạo gì cả — bỏ tham số sai này, dùng deployment mới nhất của
// workspace (audit operation, không cần chỉ định deploymentId cụ thể qua
// route công khai này).
export const captureComplianceSnapshotApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/snapshots", expose: false },
  async (req: CaptureSnapshotRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return captureComplianceSnapshot(ctx.workspaceId);
  }
);

export const listComplianceSnapshotsApi = api(
  { method: "GET", path: "/finance-legal/ai-compliance/snapshots", expose: true },
  async (req: ListSnapshotsRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return listSnapshots(ctx.workspaceId);
  }
);

export const verifyComplianceSnapshotApi = api(
  { method: "POST", path: "/finance-legal/ai-compliance/snapshots/:id/verify", expose: true },
  async (req: VerifySnapshotRequest) => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    const valid = await verifySnapshotIntegrity(ctx.workspaceId, req.id);
    return { valid };
  }
);
