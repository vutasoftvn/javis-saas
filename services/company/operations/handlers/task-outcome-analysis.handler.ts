import { api, APIError, Header } from "encore.dev/api";
import {
  CAP_OUTCOME_ASSESSMENT_RECORD,
  OutcomeAssessmentView,
  RecordOutcomeAssessmentInput,
  recordOutcomeAssessment,
} from "../services/task-outcome-analysis.service";
import { verifyCosaDelegation } from "../../shared/auth/cosa-delegation.service";

/**
 * Endpoint narrow cho Outcome Analyst ghi assessment. apps/cosa gọi kèm
 * delegation token (COSA_COMPANY_DELEGATION_SECRET) scoped
 * {workspace_id, run_id, capability_ids}. Workspace, run và capability lấy từ
 * claim ĐÃ VERIFY — header X-Workspace-Id/X-Run-Id chỉ là giá trị kỳ vọng để
 * so khớp, không bao giờ là nguồn quyền (trước đây handler tin thẳng header
 * chưa ký, nên ai cũng ghi được assessment vào workspace bất kỳ).
 */
export const recordOutcomeAssessmentEndpoint = api(
  { method: "POST", path: "/operations/outcome-assessments", expose: true },
  async (
    params: RecordOutcomeAssessmentInput & {
      authorization?: Header<"Authorization">;
      workspaceId: Header<"X-Workspace-Id">;
      xRunId: Header<"X-Run-Id">;
      xRequestId: Header<"X-Analysis-Request-Id">;
    }
  ): Promise<OutcomeAssessmentView> => {
    if (!params.xRunId || !params.xRequestId || !params.workspaceId) {
      throw APIError.unauthenticated("missing delegation attribution headers");
    }
    const match = /^Bearer\s+(.+)$/i.exec((params.authorization ?? "").trim());
    if (!match) {
      throw APIError.unauthenticated("missing cosa delegation bearer token");
    }
    let claims;
    try {
      claims = verifyCosaDelegation(match[1].trim(), {
        workspaceId: params.workspaceId,
        runId: params.xRunId,
        capabilityId: CAP_OUTCOME_ASSESSMENT_RECORD,
      });
    } catch (err) {
      throw APIError.permissionDenied(`cosa delegation rejected: ${(err as Error).message}`);
    }
    const { authorization: _auth, workspaceId: _ws, xRunId: _run, xRequestId, ...input } = params;
    return recordOutcomeAssessment(
      { ...input },
      {
        workspaceId: claims.workspace_id,
        runId: claims.run_id,
        requestId: xRequestId,
        capabilityIds: claims.capability_ids,
      }
    );
  }
);
