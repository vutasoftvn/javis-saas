import { api, Header, APIError } from "encore.dev/api";
import { requireWorkerServiceAuth } from "../../shared/auth/worker-service-auth";
import {
  recordExecutiveAnalysisCallback,
  getDeliberationAuthority,
  ExecutiveAnalysisCallbackInput,
  AnalysisRecordResult,
} from "../services/executive-deliberation.service";



interface DeliberationCallbackParams {
  authorization?: Header<"Authorization">;
  serviceToken?: Header<"X-Service-Token">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  deliberationId: string;
  kind: string;
  deliberation_id: string;
  frame_version: number;
  role_key: string;
  descriptor?: Record<string, any>;
  error_detail?: string;
  deployment_pin_hash?: string;
  overlay_pin_hash?: string;
}

export const receiveExecutiveAnalysisCallbackApi = api(
  {
    expose: true,
    method: "POST",
    path: "/internal/operations/projects/:projectId/deliberations/:deliberationId/callback",
  },
  async (params: DeliberationCallbackParams): Promise<AnalysisRecordResult> => {
    await requireWorkerServiceAuth({ serviceToken: params.serviceToken, authorization: params.authorization });

    if (params.deliberationId !== params.deliberation_id) {
      throw APIError.invalidArgument("Path deliberationId does not match body deliberation_id");
    }

    const callbackInput: ExecutiveAnalysisCallbackInput = {
      kind: params.kind,
      deliberation_id: params.deliberation_id,
      frame_version: params.frame_version,
      role_key: params.role_key,
      descriptor: params.descriptor,
      error_detail: params.error_detail,
      deployment_pin_hash: params.deployment_pin_hash,
      overlay_pin_hash: params.overlay_pin_hash,
    };

    return await recordExecutiveAnalysisCallback(
      params.workspaceId,
      params.projectId,
      params.deliberationId,
      callbackInput
    );
  }
);

interface DeliberationAuthorityParams {
  authorization?: Header<"Authorization">;
  serviceToken?: Header<"X-Service-Token">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: string;
  deliberationId: string;
  roleKey: string;
  frameVersion?: number;
}

interface DeliberationAuthorityResult {
  deliberationId: string;
  frameVersion: number;
  roleKey: string;
  state: string;
  rolePin: Record<string, any>;
  question: string;
  evidenceSources: Array<Record<string, any>>;
}

export const getDeliberationAuthorityApi = api(
  {
    expose: true,
    method: "GET",
    path: "/internal/operations/projects/:projectId/deliberations/:deliberationId/authority",
  },
  async (params: DeliberationAuthorityParams): Promise<DeliberationAuthorityResult> => {
    await requireWorkerServiceAuth({ serviceToken: params.serviceToken, authorization: params.authorization });

    return await getDeliberationAuthority(
      params.workspaceId,
      params.projectId,
      params.deliberationId,
      params.roleKey,
      params.frameVersion
    );
  }
);
