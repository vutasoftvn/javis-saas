import { api, APIError, Header } from "encore.dev/api";
import { verifyCosaDelegation } from "../../shared/auth/cosa-delegation.service";
import { resolveRuntimeComplianceSnapshot } from "../services/ai-compliance-snapshot.service";

export interface ResolveRuntimeSnapshotRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization: Header<"Authorization">;
  runId: string;
  systemKey: string;
  capabilityIds: string[];
  policySnapshotHash: string;
}

function extractBearerToken(authorization: string): string {
  const match = /^Bearer\s+(.+)$/i.exec((authorization ?? "").trim());
  if (!match) {
    throw APIError.permissionDenied("Missing or malformed delegation bearer token");
  }
  return match[1];
}

/**
 * Task 3 → Task 4: điểm wire production ĐẦU TIÊN cho delegation có cấu trúc
 * COSA→Company (mint_company_delegation / verifyCosaDelegation) — trước task
 * này verifyCosaDelegation đã tồn tại nhưng zero call site thật (xem
 * task-4-brief.md). Route này dùng delegation CHỨ KHÔNG dùng
 * requireWorkspaceAccess (không phải user session — caller là apps/cosa thay
 * mặt 1 run/agent task cụ thể).
 *
 * READ-only: KHÔNG gọi consumeCosaDelegation — đọc dữ liệu approved không có
 * side effect cần chống replay (xem cosa-delegation.service.ts).
 */
export const resolveRuntimeComplianceSnapshotApi = api(
  {
    method: "POST",
    path: "/finance-legal/ai-compliance/runtime/snapshots/resolve",
    expose: false,
  },
  async (req: ResolveRuntimeSnapshotRequest) => {
    const token = extractBearerToken(req.authorization);

    if (!req.capabilityIds || req.capabilityIds.length === 0) {
      throw APIError.invalidArgument(
        "capabilityIds must be a non-empty list — cannot verify delegation scope for an empty request"
      );
    }

    // verifyCosaDelegation gốc chỉ nhận ĐÚNG 1 capabilityId/lần gọi (Task 3
    // design). Route này cần cấp phép cho NHIỀU capability trong 1 request —
    // quyết định thiết kế (xem task-4-report.md): verify tuần tự cho TỪNG
    // capabilityId được yêu cầu, cùng 1 token — token chỉ hợp lệ nếu
    // capability_ids trong claim chứa ĐỦ TẤT CẢ capability được yêu cầu
    // (không chỉ 1 trong số đó). Nếu bất kỳ capability nào không nằm trong
    // scope, toàn bộ request bị từ chối 403 — không rơi về tập con.
    for (const capabilityId of req.capabilityIds) {
      try {
        verifyCosaDelegation(token, {
          workspaceId: req.workspaceId,
          runId: req.runId,
          capabilityId,
        });
      } catch (err) {
        throw APIError.permissionDenied(
          `Delegation scope check failed for capability "${capabilityId}": ${(err as Error).message}`
        );
      }
    }

    return resolveRuntimeComplianceSnapshot({
      workspaceId: req.workspaceId,
      runId: req.runId,
      systemKey: req.systemKey,
      capabilityIds: req.capabilityIds,
      policySnapshotHash: req.policySnapshotHash,
    });
  }
);
