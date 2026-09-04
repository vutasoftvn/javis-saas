// WGA — xác thực cho các route agent-facing được gọi bởi background task của
// apps/cosa (goal_decomposition / workspace_task_sweep). Những task này KHÔNG
// có user session, chỉ có 1 cosa company-delegation JWT (ký bởi
// COSA_COMPANY_DELEGATION_SECRET, scoped {workspace_id, run_id, capability_ids}).
//
// KHÔNG dùng consumeCosaDelegation (chống replay 1-lần) ở đây: 1 sweep run
// advance NHIỀU task bằng cùng 1 token; ràng buộc "consume 1 lần / capability"
// sẽ làm call thứ 2 fail. Cửa sổ rủi ro là TTL cứng 600s của token + guard
// state-machine ở service (vd. task.advance chỉ cho 'done' từ in_progress/
// waiting_approval). Mutation ở đây là chuyển trạng thái có kiểm soát, không
// phải external side-effect như gửi tiền/email.

import { APIError } from "encore.dev/api";
import {
  verifyCosaDelegation,
  verifyCosaDelegationForCapability,
} from "./cosa-delegation.service";
import type { TenantContext } from "../types/tenant_context";

// Capability id WGA dùng trong scope delegation (apps/cosa mint kèm đúng tập này).
export const WGA_CAP_EXECUTION_PLAN_CREATE = "operations.execution_plan.create";
export const WGA_CAP_TASK_ADVANCE = "operations.task.advance";
export const WGA_CAP_TASK_LIST = "operations.task.list";

function extractBearer(authorization: string | undefined): string {
  const m = /^Bearer\s+(.+)$/i.exec((authorization ?? "").trim());
  if (!m || !m[1]) {
    throw APIError.permissionDenied("missing or malformed cosa delegation bearer token");
  }
  return m[1].trim();
}

export interface CosaTaskDelegationExpectation {
  workspaceId: string;
  capabilityId: string;
  /** Khi request mang run_id thì khớp chính xác; bỏ trống -> chỉ khớp workspace + capability. */
  runId?: string;
}

/**
 * Verify cosa delegation token và trả về 1 TenantContext tổng hợp cho service
 * dùng như context của run. `userId` = `sub` (Company member id apps/cosa đã
 * resolve khi mint), `correlationId` = `jti`.
 */
export function resolveCosaTaskContext(
  authorization: string | undefined,
  expected: CosaTaskDelegationExpectation
): TenantContext {
  const token = extractBearer(authorization);
  let claims;
  try {
    claims = expected.runId
      ? verifyCosaDelegation(token, {
          workspaceId: expected.workspaceId,
          runId: expected.runId,
          capabilityId: expected.capabilityId,
        })
      : verifyCosaDelegationForCapability(token, {
          workspaceId: expected.workspaceId,
          capabilityId: expected.capabilityId,
        });
  } catch (err) {
    throw APIError.permissionDenied(`cosa delegation rejected: ${(err as Error).message}`);
  }

  return Object.freeze({
    workspaceId: claims.workspace_id,
    userId: claims.sub,
    workforceMemberId: undefined,
    membershipRole: "cosa_agent",
    permissions: [],
    correlationId: claims.jti,
    platformUserId: null,
  });
}
