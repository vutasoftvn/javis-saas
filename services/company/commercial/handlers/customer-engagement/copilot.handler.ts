import { api, Header } from "encore.dev/api";
import { requireWorkerServiceAuth } from "../../../shared/auth/worker-service-auth";
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import {
  getCopilotSettings,
  updateCopilotSettings,
  enableCopilot,
  disableCopilot,
  CopilotSettingsDTO,
  UpdateCopilotSettingsInput,
} from "../../services/customer-engagement/copilot-settings.service";
import {
  getThreadContextForAgent,
  ThreadContextDTO,
} from "../../services/customer-engagement/thread-context.service";
import {
  requestCopilot,
  getCopilotInvocation,
  applyCopilotResult,
  recordCopilotFeedback,
  CopilotInvocationDTO,
} from "../../services/customer-engagement/copilot.service";

// Request types
export interface CopilotSettingsRequest {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface UpdateCopilotSettingsRequest extends UpdateCopilotSettingsInput {
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface GetThreadContextRequest {
  id: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface RequestCopilotRequest {
  id: string; // threadId
  intent: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface GetCopilotInvocationRequest {
  id: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface RecordCopilotFeedbackRequest {
  id: string;
  feedback: "accepted" | "edited" | "rejected";
  editedRef?: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

export interface ApplyCopilotResultRequest {
  runId: string;
  status: string;
  artifactRef?: string;
  summaryRef?: string;
  reasonCode?: string;
  evidenceRefs?: string[];
  serviceToken?: Header<"X-Service-Token">;
  authorization?: Header<"Authorization">;
}

// 1. GET /commercial/engagement/copilot/settings
export const getCopilotSettingsApi = api(
  { expose: true, method: "GET", path: "/commercial/engagement/copilot/settings" },
  async ({ workspaceId, authorization }: CopilotSettingsRequest): Promise<CopilotSettingsDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getCopilotSettings(ctx);
  }
);

// 2. PATCH /commercial/engagement/copilot/settings
export const updateCopilotSettingsApi = api(
  { expose: true, method: "PATCH", path: "/commercial/engagement/copilot/settings" },
  async ({ workspaceId, authorization, ...params }: UpdateCopilotSettingsRequest): Promise<CopilotSettingsDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return updateCopilotSettings(params, ctx);
  }
);

// 3. POST /commercial/engagement/copilot/settings/enable
export const enableCopilotApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/copilot/settings/enable" },
  async ({ workspaceId, authorization }: CopilotSettingsRequest): Promise<CopilotSettingsDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return enableCopilot(ctx);
  }
);

// 4. POST /commercial/engagement/copilot/settings/disable
export const disableCopilotApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/copilot/settings/disable" },
  async ({ workspaceId, authorization }: CopilotSettingsRequest): Promise<CopilotSettingsDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return disableCopilot(ctx);
  }
);

// 5. GET /commercial/engagement/threads/:id/context
export const getThreadContextApi = api(
  { expose: true, method: "GET", path: "/commercial/engagement/threads/:id/context" },
  async ({ id, workspaceId, authorization }: GetThreadContextRequest): Promise<ThreadContextDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getThreadContextForAgent(id, ctx);
  }
);

// 6. POST /commercial/engagement/threads/:id/copilot
export const requestCopilotApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/threads/:id/copilot" },
  async ({ id, intent, workspaceId, authorization }: RequestCopilotRequest): Promise<{ invocationId: string; runId: string }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return requestCopilot(id, { intent }, ctx);
  }
);

// 7. GET /commercial/engagement/copilot-invocations/:id
export const getCopilotInvocationApi = api(
  { expose: true, method: "GET", path: "/commercial/engagement/copilot-invocations/:id" },
  async ({ id, workspaceId, authorization }: GetCopilotInvocationRequest): Promise<CopilotInvocationDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return getCopilotInvocation(id, ctx);
  }
);

// 8. POST /commercial/engagement/copilot-invocations/:id/feedback
export const recordCopilotFeedbackApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/copilot-invocations/:id/feedback" },
  async ({ id, feedback, editedRef, workspaceId, authorization }: RecordCopilotFeedbackRequest): Promise<CopilotInvocationDTO> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return recordCopilotFeedback(id, { feedback, editedRef }, ctx);
  }
);

// 9. POST /commercial/engagement/copilot-invocations/:runId/result (Internal callback from COSA)
export const applyCopilotResultApi = api(
  { expose: true, method: "POST", path: "/commercial/engagement/copilot-invocations/:runId/result" },
  async ({ runId, status, artifactRef, summaryRef, reasonCode, evidenceRefs, serviceToken, authorization }: ApplyCopilotResultRequest): Promise<{ success: boolean }> => {
    // Callback worker dùng chung verifier JWT (spec 2026-09-25 §5); không còn
    // token tĩnh "local-dev-service-token" làm fallback.
    await requireWorkerServiceAuth({ serviceToken, authorization });
    await applyCopilotResult({ runId, status, artifactRef, summaryRef, reasonCode, evidenceRefs });
    return { success: true };
  }
);
