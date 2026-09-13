import { api, Header } from "encore.dev/api";
import {
  AiGovernanceRef,
  AiGovernanceSnapshotResult,
  getAiGovernanceSnapshot,
} from "../services/ai-governance-snapshot.service";

export { AiGovernanceRef, AiGovernanceSnapshotResult };

export interface GetAiGovernanceSnapshotRequest {
  workspaceId: string;
  projectId: string;
  policyRefs: AiGovernanceRef[];
  evaluatorRefs: AiGovernanceRef[];
  authorization?: Header<"Authorization">;
}

/**
 * Endpoint gọi bởi `apps/cosa` (Python, ngoài Encore — không thể dùng RPC nội
 * bộ `expose: false`, phải là HTTP thật giống `/cosa/schedules*` và
 * `/platform/auth/me/agent-policy-snapshot`). `expose: true` + `auth: false`
 * ở tầng Encore Gateway vì caller dùng
 * `COSA_CONTROL_DELEGATION_SECRET`-signed delegation token (không phải
 * `PLATFORM_JWT_SECRET` mà Gateway `auth: true` yêu cầu) — verify thủ công
 * bên trong `getAiGovernanceSnapshot` (cùng pattern B5 fix của
 * agent-policy.handler.ts). Đọc/ký only — không có endpoint update/mutate
 * nào đi kèm.
 */
export const getAiGovernanceSnapshotHandler = api(
  { method: "POST", path: "/cosa/ai-governance/snapshot", expose: true, auth: false },
  async (params: GetAiGovernanceSnapshotRequest): Promise<AiGovernanceSnapshotResult> => {
    const { workspaceId, projectId, policyRefs, evaluatorRefs, authorization } = params;
    return getAiGovernanceSnapshot({ workspaceId, projectId, policyRefs, evaluatorRefs }, authorization);
  }
);
