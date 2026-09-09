import { api, Header } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  SubmitTaskResultInput,
  TaskResultView,
  listOutcomeAnalysisRequests,
  submitTaskResult,
} from "../services/task-result.service";

export const submitTaskResultEndpoint = api(
  { method: "POST", path: "/operations/task-results", expose: true },
  async (
    params: SubmitTaskResultInput & {
      workspaceId: Header<"X-Workspace-Id">;
      authorization?: Header<"Authorization">;
    }
  ): Promise<TaskResultView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return submitTaskResult(params, ctx);
  }
);

export const listOutcomeAnalysisRequestsEndpoint = api(
  { method: "GET", path: "/operations/task-results/:taskResultId/analysis-requests", expose: true },
  async (params: {
    taskResultId: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<{
    requests: Array<{ id: string; status: string; analysisKind: string; contractRevision: number }>;
  }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return { requests: await listOutcomeAnalysisRequests(params.taskResultId, ctx) };
  }
);
