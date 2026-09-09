import { api, APIError, Header } from "encore.dev/api";
import {
  OutcomeAssessmentView,
  RecordOutcomeAssessmentInput,
  recordOutcomeAssessment,
} from "../services/task-outcome-analysis.service";

/**
 * Endpoint narrow cho Outcome Analyst ghi assessment. apps/cosa gọi kèm
 * delegation scope {workspace_id, run_id, request_id, capability_ids}. Slice
 * này đọc scope từ header đã ký ở tầng gateway; verify chữ ký delegation đầy
 * đủ (COSA_CONTROL_DELEGATION_SECRET) được siết ở Task 6.
 */
export const recordOutcomeAssessmentEndpoint = api(
  { method: "POST", path: "/operations/outcome-assessments", expose: true },
  async (
    params: RecordOutcomeAssessmentInput & {
      workspaceId: Header<"X-Workspace-Id">;
      xRunId: Header<"X-Run-Id">;
      xRequestId: Header<"X-Analysis-Request-Id">;
      xCapabilityIds: Header<"X-Capability-Ids">;
    }
  ): Promise<OutcomeAssessmentView> => {
    if (!params.xRunId || !params.xRequestId) {
      throw APIError.unauthenticated("missing delegation attribution headers");
    }
    return recordOutcomeAssessment(params, {
      workspaceId: params.workspaceId,
      runId: params.xRunId,
      requestId: params.xRequestId,
      capabilityIds: (params.xCapabilityIds || "").split(",").map((s) => s.trim()).filter(Boolean),
    });
  }
);
